package deploy

import (
	"context"
	"fmt"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/clients" // Adjust this path based on your actual import path
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// DeleteCustomCatalogSource removes a specified CatalogSource from a given namespace.
func DeleteCustomCatalogSource(client *clients.Settings, catalogSourceName, namespace string) error {
	ctx := context.TODO()
	err := client.K8sClient.CoreV1().ConfigMaps(namespace).Delete(ctx, catalogSourceName, metav1.DeleteOptions{})
	if err != nil {
		return fmt.Errorf("failed to delete CatalogSource %s in namespace %s: %v", catalogSourceName, namespace, err)
	}
	fmt.Println("Successfully deleted CatalogSource:", catalogSourceName, "from namespace:", namespace)
	return nil
}
