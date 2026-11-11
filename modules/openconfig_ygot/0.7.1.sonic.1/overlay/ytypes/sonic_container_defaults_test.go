package ytypes

import (
	"github.com/openconfig/goyang/pkg/yang"
	"testing"
)

type sonicUnknownFields struct {
	Map     map[string]int `path:"map"`
	Slice   []string       `path:"slice"`
	Pointer *int           `path:"pointer"`
	Bool    bool           `path:"bool"`
	Enum    int64          `path:"enum"`
}

func (*sonicUnknownFields) IsYANGGoStruct() {}
func TestSONiCUnknownContainerFieldDefaults(t *testing.T) {
	zero := 0
	tests := []struct {
		name  string
		input *sonicUnknownFields
		fail  bool
	}{
		{"nil maps slices pointers and zero scalars", &sonicUnknownFields{}, false},
		{"nonnil empty map", &sonicUnknownFields{Map: map[string]int{}}, true},
		{"nonnil empty slice", &sonicUnknownFields{Slice: []string{}}, true},
		{"nonnil zero pointer", &sonicUnknownFields{Pointer: &zero}, true},
		{"nonzero bool", &sonicUnknownFields{Bool: true}, true},
		{"nonzero enum", &sonicUnknownFields{Enum: 1}, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			schema := &yang.Entry{Name: "root", Kind: yang.DirectoryEntry, Dir: map[string]*yang.Entry{}, PerfOpts: &yang.PerformanceOpts{}}
			errs := validateContainer(schema, tt.input)
			if (errs != nil) != tt.fail {
				t.Fatalf("errors %v, want failure %v", errs, tt.fail)
			}
		})
	}
}
