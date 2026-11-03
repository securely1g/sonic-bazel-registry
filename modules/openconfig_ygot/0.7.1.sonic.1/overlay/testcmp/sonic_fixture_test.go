package testcmp

import (
	"github.com/openconfig/ygot/exampleoc"
	"github.com/openconfig/ygot/internal/sonicfixture"
	"github.com/openconfig/ygot/uexampleoc"
	"github.com/openconfig/ygot/ytypes"
)

func init() {
	for _, entry := range exampleoc.SchemaTree {
		sonicfixture.Entry(entry)
	}
	for _, entry := range uexampleoc.SchemaTree {
		sonicfixture.Entry(entry)
	}
}

// The legacy generated Schema callback returns a newly unzipped tree each time.
func sonicFixtureSchema(fn func() (*ytypes.Schema, error)) func() (*ytypes.Schema, error) {
	return func() (*ytypes.Schema, error) {
		schema, err := fn()
		if schema != nil {
			for _, entry := range schema.SchemaTree {
				sonicfixture.Entry(entry)
			}
		}
		return schema, err
	}
}
