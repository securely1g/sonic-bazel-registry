package consumer
import (
    "testing"
    "github.com/google/uuid"
)
func TestUUID(t *testing.T) {
    const value = "123e4567-e89b-12d3-a456-426614174000"
    id, err := uuid.Parse(value)
    if err != nil || id.String() != value { t.Fatalf("UUID round trip: %v %v", id, err) }
}
