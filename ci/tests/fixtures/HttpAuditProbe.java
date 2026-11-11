import java.io.IOException;
import java.lang.instrument.Instrumentation;
import java.net.CookieHandler;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/** Test-only ordinary URLConnection client and fault injection. */
public final class HttpAuditProbe {
  public static final class Seed extends CookieHandler {
    static final Seed INSTANCE = new Seed();
    static final IOException ERROR = new IOException("fixture delegate failure");
    int gets;
    int puts;
    boolean cookieReceived;
    public static void premain(String argument, Instrumentation unused) {
      CookieHandler.setDefault(INSTANCE);
    }
    @Override public Map<String, List<String>> get(URI uri, Map<String, List<String>> headers) throws IOException {
      if (uri.getPath().equals("/explode")) throw ERROR;
      gets++;
      return Collections.singletonMap("Cookie", List.of("fixture-cookie=sentinel-cookie"));
    }
    @Override public void put(URI uri, Map<String, List<String>> headers) throws IOException {
      if (uri.getPath().equals("/explode")) throw ERROR;
      puts++;
      cookieReceived = headers.keySet().stream().anyMatch("Set-Cookie"::equalsIgnoreCase);
    }
  }

  private static void fetch(String value) throws IOException {
    HttpURLConnection connection = (HttpURLConnection) URI.create(value).toURL().openConnection();
    connection.setConnectTimeout(5000);
    connection.setReadTimeout(5000);
    try (var input = connection.getInputStream()) { input.readAllBytes(); }
  }

  private static void flush(Path directory) throws Exception {
    Files.createFile(directory.resolve("flush"));
    long deadline = System.nanoTime() + 5_000_000_000L;
    while (System.nanoTime() < deadline) {
      try (var paths = Files.list(directory)) {
        for (Path path : (Iterable<Path>) paths.filter(p -> p.toString().endsWith(".jsonl"))::iterator) {
          if (Files.readString(path).contains("\"event\":\"health\"")) return;
        }
      }
      Thread.sleep(20);
    }
    throw new AssertionError("health handshake timed out");
  }

  public static void main(String[] args) throws Exception {
    String mode = args[0];
    if (mode.equals("fast")) return;
    if (mode.equals("proxy-callbacks")) {
      URI uri = URI.create(args[1]);
      CookieHandler handler = CookieHandler.getDefault();
      handler.put(uri, Collections.singletonMap(null, List.of("HTTP/1.1 200 Connection established")));
      handler.get(uri, Collections.emptyMap());
      handler.put(uri, Collections.singletonMap(null, List.of("HTTP/1.1 404 Not Found")));
      if (Seed.INSTANCE.gets != 1 || Seed.INSTANCE.puts != 2) throw new AssertionError("proxy callback delegation changed");
      return;
    }
    if (mode.equals("callbacks")) {
      for (int i = 1; i < args.length; i++) {
        URI uri = URI.create(args[i]);
        CookieHandler.getDefault().get(uri, Collections.emptyMap());
        CookieHandler.getDefault().put(uri, Collections.singletonMap(null, List.of("HTTP/1.1 200 OK")));
      }
      return;
    }
    fetch(args[1]);
    if (mode.equals("delegate")) {
      if (Seed.INSTANCE.gets != 1 || Seed.INSTANCE.puts != 1 || !Seed.INSTANCE.cookieReceived) {
        throw new AssertionError("original handler callbacks changed");
      }
      URI failure = URI.create(args[1]).resolve("/explode");
      try {
        CookieHandler.getDefault().get(failure, Collections.emptyMap());
        throw new AssertionError("get exception missing");
      } catch (IOException error) { if (error != Seed.ERROR) throw new AssertionError("get exception changed"); }
      try {
        CookieHandler.getDefault().put(failure, Collections.emptyMap());
        throw new AssertionError("put exception missing");
      } catch (IOException error) { if (error != Seed.ERROR) throw new AssertionError("put exception changed"); }
    } else if (mode.equals("fault")) {
      Path directory = Path.of(args[2]);
      Path output = directory.resolve("http-" + ProcessHandle.current().pid() + ".jsonl");
      Path saved = directory.resolve("saved");
      Files.move(output, saved);
      Files.createDirectory(output);
      fetch(args[1]);  // An unwritable observer must not break a successful transfer.
      Files.delete(output);
      Files.move(saved, output);
      flush(directory);
    } else if (mode.equals("replace")) {
      CookieHandler.setDefault(null);
      flush(Path.of(args[2]));
    } else if (mode.equals("hold")) {
      System.out.println("ready");
      System.out.flush();
      long deadline = System.nanoTime() + 10_000_000_000L;
      while (!Files.exists(Path.of(args[2])) && System.nanoTime() < deadline) Thread.sleep(20);
    }
  }
}
