package nvidiagpu

import (
	"context"
	"fmt"
	"github.com/golang/glog"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/check"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/get"
	gpuburn "github.com/rh-ecosystem-edge/nvidia-ci/internal/gpu-burn"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/gpuparams"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/inittools"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/clients"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/pod"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"strings"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func onlyburn_deployAndTestGPU() {
	By("Deploy gpu-burn pod in test-gpu-burn namespace")
	glog.V(gpuparams.GpuLogLevel).Infof("gpu-burn pod image name is: '%s', in namespace '%s'", gpuImageNames[clusterArchitecture]["burn"], gpuBurnNamespace)

	gpuBurnPod, err := gpuburn.CreateGPUBurnPod(inittools.APIClient, gpuBurnPodName, gpuBurnNamespace, gpuImageNames[clusterArchitecture]["burn"], 5*time.Minute)
	Expect(err).ToNot(HaveOccurred(), "Error creating gpu burn pod: %v", err)

	glog.V(gpuparams.GpuLogLevel).Infof("Creating gpu-burn pod '%s' in namespace '%s'",
		gpuBurnPodName, gpuBurnNamespace)

	_, err = inittools.APIClient.Pods(gpuBurnPod.Namespace).Create(context.TODO(), gpuBurnPod,
		metav1.CreateOptions{})
	Expect(err).ToNot(HaveOccurred(), "Error creating gpu-burn '%s' in "+
		"namespace '%s': %v", gpuBurnPodName, gpuBurnNamespace, err)

	glog.V(gpuparams.GpuLogLevel).Infof("The created gpuBurnPod has name: %s has status: %v ",
		gpuBurnPod.Name, gpuBurnPod.Status)

	By("Get the gpu-burn pod with label \"app=gpu-burn-app\"")
	gpuPodName, err := get.GetFirstPodNameWithLabel(inittools.APIClient, gpuBurnNamespace, gpuBurnPodLabel)
	Expect(err).ToNot(HaveOccurred(), "error getting gpu-burn pod with label "+
		"'app=gpu-burn-app' from namespace '%s' :  %v ", gpuBurnNamespace, err)
	glog.V(gpuparams.GpuLogLevel).Infof("gpuPodName is %s ", gpuPodName)

	By("Pull the gpu-burn pod object from the cluster")
	gpuPodPulled, err := pod.Pull(inittools.APIClient, gpuPodName, gpuBurnNamespace)
	Expect(err).ToNot(HaveOccurred(), "error pulling gpu-burn pod from "+
		"namespace '%s' :  %v ", gpuBurnNamespace, err)

	By("Cleanup gpu-burn pod only if cleanupAfterTest is true and gpuOperatorUpgradeToChannel is undefined")
	defer func() {
		if cleanupAfterTest && gpuOperatorUpgradeToChannel == "undefined" {
			_, err := gpuPodPulled.Delete()
			Expect(err).ToNot(HaveOccurred())
		}
	}()

	By("Wait for up to 3 minutes for gpu-burn pod to be in Running phase")
	err = gpuPodPulled.WaitUntilInStatus(corev1.PodRunning, 3*time.Minute)
	Expect(err).ToNot(HaveOccurred(), "timeout waiting for gpu-burn pod in "+
		"namespace '%s' to go to Running phase:  %v ", gpuBurnNamespace, err)
	glog.V(gpuparams.GpuLogLevel).Infof("gpu-burn pod now in Running phase")
	validateGPUPodAndLogResults(gpuPodPulled, gpuBurnNamespace, gpuPodName)
}

func validateGPUPodAndLogResults(gpuPod *pod.Builder, namespace, podName string) {
	// Wait for the GPU pod to run to completion and be in the Succeeded phase
	By(fmt.Sprintf("Wait for gpu-burn pod '%s' to run to completion and be in Succeeded phase/Completed status", podName))
	err := gpuPod.WaitUntilInStatus(corev1.PodSucceeded, 8*time.Minute)
	Expect(err).ToNot(HaveOccurred(), "timeout waiting for gpu-burn pod '%s' in namespace '%s' to go Succeeded phase/Completed status: %v", podName, namespace, err)
	glog.V(gpuparams.GpuLogLevel).Infof("gpu-burn pod '%s' now in Succeeded Phase/Completed status", podName)

	// Retrieve the logs from the GPU pod
	By(fmt.Sprintf("Get the gpu-burn pod logs for pod '%s'", podName))
	glog.V(gpuparams.GpuLogLevel).Infof("Retrieving the gpu-burn pod logs")
	gpuBurnLogs, err := gpuPod.GetLog(500*time.Second, "gpu-burn-ctr")
	Expect(err).ToNot(HaveOccurred(), "error getting gpu-burn pod '%s' logs from gpu burn namespace '%s': %v", podName, namespace, err)
	glog.V(gpuparams.GpuLogLevel).Infof("Gpu-burn pod '%s' logs:\n%s", podName, gpuBurnLogs)

	// Check for success indicators in the pod logs
	By("Parse the gpu-burn pod logs and check for successful execution")
	match1 := strings.Contains(gpuBurnLogs, "GPU 0: OK")
	match2 := strings.Contains(gpuBurnLogs, "100.0%  proc'd:")
	Expect(match1 && match2).ToNot(BeFalse(), "gpu-burn pod execution was FAILED for pod '%s'", podName)
	glog.V(gpuparams.GpuLogLevel).Infof("Execution of gpu-burn pod '%s' verified successfully", podName)
}

func redeployGpuBurnPod() {
	By("Re-deploy gpu-burn pod in test-gpu-burn namespace")
	glog.V(gpuparams.GpuLogLevel).Infof("Re-deployed gpu-burn pod image name is: '%s', in "+
		"namespace '%s'", gpuImageNames[clusterArchitecture]["burn"], gpuBurnNamespace)

	By("Get Cluster Architecture from first GPU enabled worker node")
	glog.V(gpuparams.GpuLogLevel).Infof("Getting cluster architecture from nodes with "+
		"gpuWorkerNodeSelector: %v", gpuWorkerNodeSelector)
	clusterArch, err := get.GetClusterArchitecture(inittools.APIClient, gpuWorkerNodeSelector)
	Expect(err).ToNot(HaveOccurred(), "error getting cluster architecture:  %v ", err)

	glog.V(gpuparams.GpuLogLevel).Infof("cluster architecture for GPU enabled worker node is: %s",
		clusterArch)

	gpuBurnPod2, err := gpuburn.CreateGPUBurnPod(inittools.APIClient, gpuBurnPodName, gpuBurnNamespace,
		gpuImageNames[clusterArch]["burn"], 5*time.Minute)
	Expect(err).ToNot(HaveOccurred(), "Error re-building gpu burn pod object after "+
		"upgrade: %v", err)

	glog.V(gpuparams.GpuLogLevel).Infof("Re-deploying gpu-burn pod '%s' in namespace '%s'",
		gpuBurnPodName, gpuBurnNamespace)

	_, err = inittools.APIClient.Pods(gpuBurnNamespace).Create(context.TODO(), gpuBurnPod2,
		metav1.CreateOptions{})
	Expect(err).ToNot(HaveOccurred(), "Error re-deploying gpu-burn '%s' after operator"+
		" upgrade in namespace '%s': %v", gpuBurnPodName, gpuBurnNamespace, err)

	glog.V(gpuparams.GpuLogLevel).Infof("The re-deployed post upgrade gpuBurnPod has name: %s has "+
		"status: %v ", gpuBurnPod2.Name, gpuBurnPod2.Status)

	By("Get the re-deployed gpu-burn pod with label \"app=gpu-burn-app\"")
	gpuBurnPod2Name, err := get.GetFirstPodNameWithLabel(inittools.APIClient, gpuBurnNamespace, gpuBurnPodLabel)
	Expect(err).ToNot(HaveOccurred(), "error getting re-deployed gpu-burn pod with label "+
		"'app=gpu-burn-app' from namespace '%s' :  %v ", gpuBurnNamespace, err)
	glog.V(gpuparams.GpuLogLevel).Infof("gpuPodName is %s ", gpuBurnPod2Name)

	By("Pull the re-created gpu-burn pod object from the cluster")
	gpuBurnPod2Pulled, err := pod.Pull(inittools.APIClient, gpuBurnPod2.Name, gpuBurnNamespace)
	Expect(err).ToNot(HaveOccurred(), "error pulling re-deployed gpu-burn pod from "+
		"namespace '%s' :  %v ", gpuBurnNamespace, err)

	defer func() {
		if cleanupAfterTest {
			_, err := gpuBurnPod2Pulled.Delete()
			Expect(err).ToNot(HaveOccurred())
		}
	}()

	By("Wait for up to 3 minutes for re-deployed gpu-burn pod to be in Running phase")
	err = gpuBurnPod2Pulled.WaitUntilInStatus(corev1.PodRunning, 3*time.Minute)
	Expect(err).ToNot(HaveOccurred(), "timeout waiting for re-deployed gpu-burn pod in "+
		"namespace '%s' to go to Running phase:  %v ", gpuBurnNamespace, err)
	glog.V(gpuparams.GpuLogLevel).Infof("gpu-burn pod now in Running phase")

	validateGPUPodAndLogResults(gpuBurnPod2Pulled, gpuBurnNamespace, gpuBurnPod2Name)
}

func cleanupPreviousDeployment() {
	By("Pull the previously deployed gpu-burn pod object from the cluster")
	currentGpuBurnPodPulled, err := pod.Pull(inittools.APIClient, gpuBurnPodName, gpuBurnNamespace)
	Expect(err).ToNot(HaveOccurred(), "error pulling previously deployed and completed "+
		"gpu-burn pod from namespace '%s' :  %v ", gpuBurnNamespace, err)

	By("Get the gpu-burn pod with label \"app=gpu-burn-app\"")
	currentGpuBurnPodName, err := get.GetFirstPodNameWithLabel(inittools.APIClient, gpuBurnNamespace,
		gpuBurnPodLabel)
	Expect(err).ToNot(HaveOccurred(), "error getting previously deployed gpu-burn pod "+
		"with label 'app=gpu-burn-app' from namespace '%s' :  %v ", gpuBurnNamespace, err)
	glog.V(gpuparams.GpuLogLevel).Infof("gpuPodName is %s ", currentGpuBurnPodName)

	By("Delete the previously deployed gpu-burn-pod")
	glog.V(gpuparams.GpuLogLevel).Infof("Deleting previously deployed and completed gpu-burn pod")

	_, err = currentGpuBurnPodPulled.Delete()
	Expect(err).ToNot(HaveOccurred(), "Error deleting gpu-burn pod")
}

func checkNfdInstallation(apiClient *clients.Settings, label, labelValue string, workerLabelMap map[string]string, logLevel int) {
	By(fmt.Sprintf("Check if NFD is installed using label: %s", label))
	nfdLabelDetected, err := check.AllNodeLabel(apiClient, label, labelValue, workerLabelMap)
	Expect(err).ToNot(HaveOccurred(), "error calling check.NodeLabel: %v", err)
	Expect(nfdLabelDetected).NotTo(BeFalse(), "NFD node label check failed to match label %s and label value %s on all nodes", label, labelValue)
	glog.V(glog.Level(logLevel)).Infof("The check for NFD label returned: %v", nfdLabelDetected)

	isNfdInstalled, err := check.NFDDeploymentsReady(apiClient)
	Expect(err).ToNot(HaveOccurred(), "error checking if NFD deployments are ready: %v", err)
	glog.V(glog.Level(logLevel)).Infof("The check for NFD deployments ready returned: %v", isNfdInstalled)
}
