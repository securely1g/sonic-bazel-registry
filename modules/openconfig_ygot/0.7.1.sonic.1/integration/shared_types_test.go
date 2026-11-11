package consumer

import (
	"testing"

	"github.com/openconfig/goyang/pkg/yang"
	"github.com/openconfig/ygot/ygot"
	"github.com/openconfig/ygot/ytypes"
)

func TestSourceOwnersShareTheSameYANGType(t *testing.T) {
	// The direct shared goyang dependency must have exactly the Go type accepted
	// by ygot's public validator, including SONiC's legacy performance fields.
	schema := &yang.Entry{
		Name: "selected", Kind: yang.LeafEntry,
		Type: &yang.YangType{Kind: yang.Ystring}, PerfOpts: &yang.PerformanceOpts{},
	}
	if errors := ytypes.Validate(schema, ygot.String("selected")); len(errors) != 0 {
		t.Fatalf("shared schema/string validation failed: %v", errors)
	}
	if errors := ytypes.Validate(schema, ygot.Uint64(42)); len(errors) == 0 {
		t.Fatal("string schema accepted an integer")
	}
}
