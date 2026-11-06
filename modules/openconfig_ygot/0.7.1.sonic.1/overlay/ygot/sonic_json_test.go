package ygot

import (
	"bytes"
	"encoding/json"
	"testing"
)

// SONiC emits compact JSON. Preserve every original expected token and its order.
func sonicCompactJSON(t *testing.T, data []byte) []byte {
	t.Helper()
	var out bytes.Buffer
	if err := json.Compact(&out, data); err != nil {
		t.Fatal(err)
	}
	return out.Bytes()
}
