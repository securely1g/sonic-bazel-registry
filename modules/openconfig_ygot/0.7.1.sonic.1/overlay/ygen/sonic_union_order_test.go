package ygen

import (
	"strings"
	"testing"
)

func TestSONiCUnionEnumReflectionOrder(t *testing.T) {
	var first string
	for round := 0; round < 64; round++ {
		generator := NewYANGCodeGenerator(&GeneratorConfig{
			PackageName: "ordering", Caller: "sonic-ordering-test",
			GenerateJSONSchema: true,
		})
		generated, errors := generator.GenerateGoCode([]string{"sonic_union_order.yang"}, nil)
		if len(errors) != 0 {
			t.Fatal(errors)
		}
		reflection := strings.ToLower(generated.EnumTypeMap)
		zulu, alpha := strings.Index(reflection, "zulu"), strings.Index(reflection, "alpha")
		if zulu < 0 || alpha <= zulu || !strings.Contains(reflection, "/selected") {
			t.Fatalf("declared union order lost in reflection map: %s", generated.EnumTypeMap)
		}
		if round == 0 {
			first = generated.EnumTypeMap
		} else if first != generated.EnumTypeMap {
			t.Fatalf("round %d changed the union reflection output", round)
		}
	}
}
