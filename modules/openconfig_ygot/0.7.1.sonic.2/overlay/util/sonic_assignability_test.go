package util

import (
	"reflect"
	"testing"
)

type sonicTestBool bool
type sonicTestBytes []byte
type sonicTestNamedInt int
type sonicTestStringer struct{}

func (sonicTestStringer) String() string { return "value" }

func TestSONiCStructAssignmentCompatibility(t *testing.T) {
	type fields struct {
		Bool     sonicTestBool
		Bytes    sonicTestBytes
		Number   *int
		Any      interface{}
		Stringer interface{ String() string }
		Named    sonicTestNamedInt
		Map      map[string]string
	}
	number := 42
	tests := []struct {
		name, field string
		value, want interface{}
		fail        bool
	}{
		{"derived bool", "Bool", true, sonicTestBool(true), false},
		{"derived binary", "Bytes", []byte("sonic"), sonicTestBytes("sonic"), false},
		{"pointer adaptation", "Number", number, &number, false},
		{"pointer identity", "Number", &number, &number, false},
		{"nil pointer", "Number", nil, (*int)(nil), false},
		{"empty interface", "Any", []string{"sonic"}, []string{"sonic"}, false},
		{"implemented interface", "Stringer", sonicTestStringer{}, sonicTestStringer{}, false},
		{"same named type", "Named", sonicTestNamedInt(42), sonicTestNamedInt(42), false},
		{"incompatible slice", "Bytes", []string{"one", "two"}, nil, true},
		{"incompatible pointer", "Number", new(string), nil, true},
		{"incompatible map", "Map", map[string]int{"one": 1}, nil, true},
		{"different named type", "Named", number, nil, true},
		{"unimplemented interface", "Stringer", number, nil, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := &fields{}
			err := InsertIntoStruct(got, tt.field, tt.value)
			if (err != nil) != tt.fail {
				t.Fatalf("error=%v, want failure=%v", err, tt.fail)
			}
			if !tt.fail && !reflect.DeepEqual(reflect.ValueOf(got).Elem().FieldByName(tt.field).Interface(), tt.want) {
				t.Fatalf("field=%v want=%v", reflect.ValueOf(got).Elem().FieldByName(tt.field).Interface(), tt.want)
			}
		})
	}
}
