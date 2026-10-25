CHECK = $(CXX) $(CXXFLAGS) $(CPPFLAGS) -Werror -Wall -Wextra -Wmissing-include-dirs -fsyntax-only
.PHONY: all install
all:
	$(CHECK) system.cc
	$(CHECK) lookup.cc
	@if $(CHECK) ordinary.cc > ordinary.log 2>&1; then cat ordinary.log; echo 'ordinary header warnings were suppressed'; exit 1; fi
	@grep -q 'unused parameter' ordinary.log
	@if $(CHECK) -isystem$(CURDIR)/deliberately-missing system.cc > missing.log 2>&1; then echo 'missing-directory diagnostics were suppressed'; exit 1; fi
	@grep -q 'missing-include-dirs' missing.log
	@if $(CHECK) angle_quote.cc > angle_quote.log 2>&1; then echo 'quote-only header leaked into angle lookup'; exit 1; fi
	@grep -q 'quote_only.h' angle_quote.log
install: all
	printf 'Make: system diagnostics and quote/ordinary lookup verified\n' > $(PREFIX)/receipt.txt
