package deploy

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestDeploy(t *testing.T) {

	RegisterFailHandler(Fail)
	RunSpecs(t, "Deploy Suite")
}
