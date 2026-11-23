import java.io.IOException;
import java.io.Reader;
import java.lang.instrument.Instrumentation;
import java.net.CookieHandler;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.StandardWatchEventKinds;
import java.nio.file.WatchKey;
import java.nio.file.WatchService;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.TimeUnit;

/** Observe Bazel's existing HttpURLConnection downloader without changing its transport.
 * Response events describe HTTP headers, not completed or checksum-verified downloads.
 */
public final class DebianHttpAudit extends CookieHandler {
  private final CookieHandler previous;
  private final List<Mirror> mirrors;
  private final Path directory;
  private final Path output;
  private final long pid = ProcessHandle.current().pid();
  private volatile boolean recordingFailed;
  // Correlate a followed redirect on the downloader thread without retaining Location,
  // credentials, or query text. Unknown external destinations never get a path in evidence.
  private final ThreadLocal<Redirect> nextRedirect = new ThreadLocal<>();
  private final ThreadLocal<Redirect> activeRedirect = new ThreadLocal<>();
  private final ThreadLocal<String> requestedUri = new ThreadLocal<>();

  private static final class Redirect {
    final String fingerprint;
    final String object;
    Redirect(String fingerprint, String object) {
      this.fingerprint = fingerprint;
      this.object = object;
    }
  }

  private static final class Mirror {
    final URI base;
    final String mount;

    Mirror(String value) {
      base = URI.create(value);
      int archive = base.getRawPath().lastIndexOf("/archive/");
      if (!"https".equalsIgnoreCase(base.getScheme()) || base.getHost() == null
          || base.getUserInfo() != null || base.getQuery() != null || base.getFragment() != null
          || archive < 0) throw new IllegalArgumentException("Invalid mirror configuration");
      mount = base.getRawPath().substring(0, archive);
    }

    boolean host(URI uri) { return base.getHost().equalsIgnoreCase(uri.getHost()); }
    boolean origin(URI uri) {
      return host(uri) && "https".equalsIgnoreCase(uri.getScheme())
          && port(base) == port(uri);
    }
  }

  private static final class Location {
    final String origin;
    final String type;
    final String path;
    final String object;
    Location(String origin, String type, String path) {
      this(origin, type, path, null);
    }
    Location(String origin, String type, String path, String object) {
      this.origin = origin;
      this.type = type;
      this.path = path;
      this.object = object;
    }
  }

  private DebianHttpAudit(Properties properties) throws IOException {
    previous = CookieHandler.getDefault();
    directory = Path.of(properties.getProperty("output"));
    if (!directory.isAbsolute() || !Files.isDirectory(directory)) {
      throw new IllegalArgumentException("Invalid audit output directory");
    }
    mirrors = new ArrayList<>();
    for (int i = 0; properties.containsKey("mirror." + i); i++) {
      mirrors.add(new Mirror(properties.getProperty("mirror." + i)));
    }
    if (mirrors.isEmpty()) throw new IllegalArgumentException("No audit mirrors configured");
    output = directory.resolve("http-" + pid + ".jsonl");
    Files.createFile(output, PosixFilePermissions.asFileAttribute(
        PosixFilePermissions.fromString("rw-------")));
  }

  public static void premain(String configuration, Instrumentation unused) {
    try {
      Properties properties = new Properties();
      try (Reader input = Files.newBufferedReader(Path.of(configuration), StandardCharsets.UTF_8)) {
        properties.load(input);
      }
      DebianHttpAudit observer = new DebianHttpAudit(properties);
      CookieHandler.setDefault(observer);
      observer.health("installed");
      Runtime.getRuntime().addShutdownHook(new Thread(() -> observer.health("shutdown"),
          "debian-http-audit-shutdown"));
      Thread watcher = new Thread(observer::watchForFlush, "debian-http-audit-health");
      watcher.setDaemon(true);
      watcher.start();
    } catch (Exception error) {
      // Startup diagnostics must not expose the configuration, endpoint, or scratch path.
      System.err.println("Debian HTTP audit unavailable; download observation is incomplete.");
    }
  }

  private static int port(URI uri) {
    return uri.getPort() >= 0 ? uri.getPort() : ("https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80);
  }

  private static boolean loopback(String host) {
    return "localhost".equals(host) || "127.0.0.1".equals(host)
        || "::1".equals(host) || "[::1]".equals(host);
  }

  private Location locate(URI uri, Redirect redirected) {
    if (!("http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme()))
        || uri.getHost() == null) return null;
    String host = uri.getHost().toLowerCase(Locale.ROOT);
    boolean privateOrigin = false;
    String path = uri.getRawPath();
    String mount = null;
    boolean knownHost = false;
    for (Mirror mirror : mirrors) {
      if (!mirror.host(uri)) continue;
      knownHost = true;
      privateOrigin |= mirror.origin(uri);
      if (path != null && path.startsWith(mirror.mount + "/")
          && (mount == null || mirror.mount.length() > mount.length())) mount = mirror.mount;
    }
    if (loopback(host) && !privateOrigin) return null;
    boolean official = "debian.org".equals(host) || host.endsWith(".debian.org");
    if (redirected != null && !privateOrigin) {
      return new Location("public", "redirect", null, redirected.object);
    }
    if (knownHost) path = mount == null ? "/private-object" : path.substring(mount.length());
    if (path == null || path.length() > 8192) {
      recordingFailed = true;
      path = "/unavailable-object";
    }
    String type;
    if (path.matches(".*\\.(?:deb|udeb|ddeb)$")) type = "binary";
    else if (!(privateOrigin || official || knownHost)) return null;
    else if (path.matches("/file/[0-9a-fA-F]{40}")) type = "content-addressed";
    else if (path.contains("/dists/")) type = "index";
    else if (path.contains("/pool/") && path.matches(".*\\.(?:dsc|diff\\.gz|tar\\.(?:gz|bz2|xz|lzma|zst))$")) type = "source";
    else type = "other";
    return new Location(privateOrigin ? "private" : "public", type, path);
  }

  private static String fingerprint(URI uri) throws Exception {
    return Base64.getEncoder().encodeToString(MessageDigest.getInstance("SHA-256")
        .digest(uri.toString().getBytes(StandardCharsets.UTF_8)));
  }

  @Override
  public Map<String, List<String>> get(URI uri, Map<String, List<String>> requestHeaders) throws IOException {
    Map<String, List<String>> result = previous == null ? Collections.emptyMap()
        : previous.get(uri, requestHeaders);
    try {
      Redirect pending = nextRedirect.get();
      nextRedirect.remove();
      boolean redirected = pending != null && pending.fingerprint.equals(fingerprint(uri));
      if (redirected) activeRedirect.set(pending);
      else activeRedirect.remove();
      Location location = locate(uri, redirected ? pending : null);
      if (location == null) requestedUri.remove();
      else requestedUri.set(fingerprint(uri));
      event("request", location, 0);
    } catch (Exception error) { recordingFailed = true; }
    return result;
  }

  @Override
  public void put(URI uri, Map<String, List<String>> responseHeaders) throws IOException {
    try {
      String request = requestedUri.get();
      // A proxy CONNECT acknowledgement can call put before the object's get.
      // It is not a response to the download request. Delegate it, but do not
      // attribute it or disturb a pending redirect to the next connection.
      if (request != null && request.equals(fingerprint(uri))) {
        requestedUri.remove();
        Redirect active = activeRedirect.get();
        Location location = locate(uri, active != null && active.fingerprint.equals(request) ? active : null);
        int status = status(responseHeaders);
        event("response", location, status);
        nextRedirect.remove();
        if (location != null && status >= 300 && status < 400) {
          for (Map.Entry<String, List<String>> header : responseHeaders.entrySet()) {
            if ("Location".equalsIgnoreCase(header.getKey()) && !header.getValue().isEmpty()) {
              nextRedirect.set(new Redirect(fingerprint(uri.resolve(header.getValue().get(0))),
                  location.object == null ? location.path : location.object));
              break;
            }
          }
        }
      }
    } catch (Exception error) { recordingFailed = true; }
    if (previous != null) previous.put(uri, responseHeaders);
  }

  private static int status(Map<String, List<String>> headers) {
    List<String> lines = headers.get(null);
    if (lines != null && !lines.isEmpty()) {
      String[] words = lines.get(0).split("\\s+", 3);
      if (words.length >= 2 && words[0].startsWith("HTTP/") && words[1].matches("[0-9]{3}")) {
        return Integer.parseInt(words[1]);
      }
    }
    return 0;
  }

  private void event(String event, Location location, int status) {
    if (location == null) return;
    write("\"event\":" + quote(event) + ",\"origin\":" + quote(location.origin)
        + ",\"type\":" + quote(location.type)
        + (location.path == null ? "" : ",\"path\":" + quote(location.path))
        + (location.object == null ? "" : ",\"object\":" + quote(location.object))
        + ("response".equals(event) ? ",\"status\":" + status : ""));
  }

  private void health(String event) {
    write("\"event\":" + quote(event) + ",\"handler_still_installed\":"
        + (CookieHandler.getDefault() == this) + ",\"recording_failed\":" + recordingFailed
        + ("installed".equals(event) ? ",\"had_delegate\":" + (previous != null) : ""));
  }

  private synchronized void write(String fields) {
    try {
      Files.writeString(output, "{\"schema_version\":1,\"pid\":" + pid + "," + fields + "}\n",
          StandardCharsets.UTF_8, StandardOpenOption.WRITE, StandardOpenOption.APPEND,
          LinkOption.NOFOLLOW_LINKS);
    } catch (IOException | RuntimeException error) { recordingFailed = true; }
  }

  private void watchForFlush() {
    try (WatchService watcher = directory.getFileSystem().newWatchService()) {
      directory.register(watcher, StandardWatchEventKinds.ENTRY_CREATE);
      while (Files.isDirectory(directory)) {
        if (Files.exists(directory.resolve("flush"))) {
          health("health");
          return;
        }
        WatchKey key = watcher.poll(1, TimeUnit.SECONDS);
        if (key != null) {
          key.pollEvents();
          if (!key.reset()) return;
        }
      }
    } catch (Exception error) { recordingFailed = true; }
  }

  private static String quote(String value) {
    StringBuilder escaped = new StringBuilder("\"");
    for (char character : value.toCharArray()) {
      if (character == '\\' || character == '"') escaped.append('\\').append(character);
      else if (character < 32) escaped.append(String.format("\\u%04x", (int) character));
      else escaped.append(character);
    }
    return escaped.append('"').toString();
  }
}
