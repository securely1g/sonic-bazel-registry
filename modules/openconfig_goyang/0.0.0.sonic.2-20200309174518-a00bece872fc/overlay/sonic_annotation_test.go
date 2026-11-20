package main

import (
	"bytes"
	"strings"
	"testing"

	"github.com/openconfig/goyang/pkg/yang"
)

func TestSONiCAnnotationFormatter(t *testing.T) {
	ms := yang.NewModules()
	if err := ms.Parse(`module example {
	 yang-version 1; namespace "urn:example"; prefix ex;
	 container root { leaf selected { type string; } }
	}`, "example.yang"); err != nil {
		t.Fatal(err)
	}
	if errors := ms.Process(); len(errors) != 0 {
		t.Fatal(errors)
	}
	f, ok := formatters["annotate"]
	if !ok || f.utilf == nil {
		t.Fatal("SONiC annotation formatter is missing")
	}
	f.utilf([]string{"example.yang"}, ms.Modules)
	var output bytes.Buffer
	f.f(&output, []*yang.Entry{yang.ToEntry(ms.Modules["example"])})
	for _, expected := range []string{"module example-annot", "import example", "/ex:root/ex:selected"} {
		if !strings.Contains(output.String(), expected) {
			t.Fatalf("annotation output omits %q: %s", expected, output.String())
		}
	}
}
