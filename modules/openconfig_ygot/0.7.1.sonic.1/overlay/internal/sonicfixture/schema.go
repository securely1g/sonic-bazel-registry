// Package sonicfixture initializes the performance state omitted from old,
// handwritten and pre-generated upstream test schemas. It is test-only.
package sonicfixture

import "github.com/openconfig/goyang/pkg/yang"

// Entry preserves every schema field and existing cache while supplying the
// state that the actual SONiC parser/generator creates for each entry.
func Entry(root *yang.Entry) *yang.Entry {
	seen := map[*yang.Entry]bool{}
	var visit func(*yang.Entry)
	visit = func(entry *yang.Entry) {
		if entry == nil || seen[entry] {
			return
		}
		seen[entry] = true
		if entry.PerfOpts == nil {
			entry.PerfOpts = &yang.PerformanceOpts{}
		}
		for _, child := range entry.Dir {
			visit(child)
		}
		visit(entry.Parent)
	}
	visit(root)
	return root
}
