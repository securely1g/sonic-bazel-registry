package validate

import (
	"github.com/openconfig/ygot/exampleoc"
	"github.com/openconfig/ygot/internal/sonicfixture"
	"github.com/openconfig/ygot/uexampleoc"
)

func init() {
	for _, entry := range exampleoc.SchemaTree {
		sonicfixture.Entry(entry)
	}
	for _, entry := range uexampleoc.SchemaTree {
		sonicfixture.Entry(entry)
	}
}
