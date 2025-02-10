package nvidiagpu

import (
	"github.com/operator-framework/api/pkg/operators/v1alpha1"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/inittools"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/nvidiagpuconfig"
)

var (
	gpuInstallPlanApproval v1alpha1.Approval = "Automatic"

	gpuWorkerNodeSelector = map[string]string{
		inittools.GeneralConfig.WorkerLabel:           "",
		"feature.node.kubernetes.io/pci-10de.present": "true",
	}

	//gpuBurnImageName = map[string]string{
	//	"amd64": "quay.io/wabouham/gpu_burn_amd64:ubi9",
	//	"arm64": "quay.io/wabouham/gpu_burn_arm64:ubi9",
	//}
	////adding more test workloads
	//gpuLightBurnImageName = map[string]string{
	//	"amd64": "nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda12.5.0-ubi8",
	//	"arm64": "nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda12.5.0-ubi8",
	//}

	gpuImageNames = map[string]map[string]string{
		"amd64": {
			"burn":  "quay.io/wabouham/gpu_burn_amd64:ubi9",
			"light": "nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda12.5.0-ubi8",
		},
		"arm64": {
			"burn":  "quay.io/wabouham/gpu_burn_arm64:ubi9",
			"light": "nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda12.5.0-ubi8",
		},
	}

	machineSetNamespace         = "openshift-machine-api"
	replicas              int32 = 1
	workerMachineSetLabel       = "machine.openshift.io/cluster-api-machine-role"

	nfdCleanupAfterInstall bool = false

	// NvidiaGPUConfig provides access to general configuration parameters.
	nvidiaGPUConfig                  *nvidiagpuconfig.NvidiaGPUConfig
	gpuScaleCluster                  bool = false
	gpuCatalogSource                      = "undefined"
	nfdCatalogSource                      = "undefined"
	gpuCustomCatalogSource                = "undefined"
	nfdCustomCatalogSource                = "undefined"
	createGPUCustomCatalogsource     bool = false
	createNFDCustomCatalogsource     bool = false
	gpuCustomCatalogsourceIndexImage      = "undefined"
	nfdCustomCatalogsourceIndexImage      = "undefined"
	gpuSubscriptionChannel                = "undefined"
	gpuDefaultSubscriptionChannel         = "undefined"
	gpuOperatorUpgradeToChannel           = "undefined"
	cleanupAfterTest                 bool = true
	deployFromBundle                 bool = false
	gpuOperatorBundleImage                = ""
	gpuCurrentCSV                         = ""
	gpuCurrentCSVVersion                  = ""
	clusterArchitecture                   = "undefined"
)
