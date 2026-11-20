package yang

import (
	"reflect"
	"testing"
)

// Exercise the public API retained by SONiC's selected ygot, including ordered
// children and the PerformanceOpts field absent from current upstream goyang.
func TestSONiCChoicePreservesDeclaredChildren(t *testing.T) {
	choice := &Entry{Name: "mode", Kind: ChoiceEntry,
		Dir: map[string]*Entry{
			"zulu":  {Name: "zulu", Kind: LeafEntry, Node: &Leaf{Name: "zulu"}},
			"alpha": {Name: "alpha", Kind: LeafEntry, Node: &Leaf{Name: "alpha"}},
		}, DirOKeys: []string{"zulu", "alpha"}, PerfOpts: &PerformanceOpts{}}
	choice.FixChoice()
	if want := []string{"zulu", "alpha"}; !reflect.DeepEqual(choice.DirOKeys, want) {
		t.Fatalf("choice order/duplicates: got %v, want %v", choice.DirOKeys, want)
	}
	for _, name := range choice.DirOKeys {
		child := choice.Dir[name]
		if child.Kind != CaseEntry || child.PerfOpts == nil ||
			!reflect.DeepEqual(child.DirOKeys, []string{name}) || child.Dir[name].Parent != child {
			t.Fatalf("implicit case lost SONiC child contract: %#v", child)
		}
	}
}

func TestSONiCGroupingAndAugmentOrder(t *testing.T) {
	texts := []string{
		`module base { namespace "urn:base"; prefix b;
		 grouping leaves { leaf zulu {type string;} leaf alpha {type string;} }
		 container root { uses leaves; }
		}`,
		`module zed { namespace "urn:zed"; prefix z; import base {prefix b;}
		 augment "/b:root" { leaf zed {type string;} }
		}`,
		`module aleph { namespace "urn:aleph"; prefix a; import base {prefix b;}
		 augment "/b:root" { leaf aleph {type string;} }
		}`,
	}
	for round := 0; round < 64; round++ {
		ms := NewModules()
		for i, text := range texts {
			if err := ms.Parse(text, []string{"base.yang", "zed.yang", "aleph.yang"}[i]); err != nil {
				t.Fatal(err)
			}
		}
		if errors := ms.Process(); len(errors) != 0 {
			t.Fatal(errors)
		}
		entry := ToEntry(ms.Modules["base"]).Dir["root"]
		if want := []string{"zulu", "alpha", "aleph", "zed"}; !reflect.DeepEqual(entry.DirOKeys, want) {
			t.Fatalf("round %d: grouping/augment order %v, want %v", round, entry.DirOKeys, want)
		}
	}
}

func TestSONiCIdentityOrder(t *testing.T) {
	for round := 0; round < 64; round++ {
		ms := NewModules()
		if err := ms.Parse(`module identities { namespace "urn:identities"; prefix i;
		 identity ROOT;
		 identity ZULU {base ROOT;}
		 identity ALPHA {base ROOT;}
		 identity MIDDLE {base ROOT;}
		 leaf selected {type identityref {base ROOT;}}
		}`, "identities.yang"); err != nil {
			t.Fatal(err)
		}
		if errors := ms.Process(); len(errors) != 0 {
			t.Fatal(errors)
		}
		root := ToEntry(ms.Modules["identities"]).Dir["selected"].Type.IdentityBase
		var names []string
		for _, identity := range root.Values {
			names = append(names, identity.Name)
		}
		if want := []string{"ALPHA", "MIDDLE", "ZULU"}; !reflect.DeepEqual(names, want) {
			t.Fatalf("round %d: identity order %v, want %v", round, names, want)
		}
	}
}

// SONiC deliberately drops the duplicated Entry description, but preserves the
// original schema's AST. There is no public switch for retaining Entry text.
func TestSONiCDescriptionMemoryContract(t *testing.T) {
	ms := NewModules()
	if err := ms.Parse(`module descriptions { namespace "urn:descriptions"; prefix d;
 leaf value { type string; description "original schema description"; }
 }`, "descriptions.yang"); err != nil {
		t.Fatal(err)
	}
	if errs := ms.Process(); len(errs) != 0 {
		t.Fatal(errs)
	}
	leaf := ToEntry(ms.Modules["descriptions"]).Dir["value"]
	if leaf.Description != "" {
		t.Fatalf("Entry description was retained: %q", leaf.Description)
	}
	ast, ok := leaf.Node.(*Leaf)
	if !ok || ast.Description == nil || ast.Description.Name != "original schema description" {
		t.Fatalf("original AST description was lost: %#v", leaf.Node)
	}
}
