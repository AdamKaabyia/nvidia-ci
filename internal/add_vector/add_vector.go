package add_vector

import (
	"time"

	"github.com/golang/glog"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/gpuparams"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/clients"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/configmap"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var (
	isFalse bool = false
	isTrue  bool = true

	cudaSampleConfigMapData = map[string]string{
		"entrypoint.sh": `#!/bin/bash
		./vectorAdd`,
	}
)

// CreateCUDASampleConfigMap returns a configmap with data field populated.
func CreateCUDASampleConfigMap(apiClient *clients.Settings,
	configMapName, configMapNamespace string) (*corev1.ConfigMap, error) {
	configMapBuilder := configmap.NewBuilder(apiClient, configMapName, configMapNamespace)

	configMapBuilderWithData := configMapBuilder.WithData(cudaSampleConfigMapData)

	createdConfigMapBuilderWithData, err := configMapBuilderWithData.Create()

	if err != nil {
		glog.V(gpuparams.GpuLogLevel).Infof(
			"error creating ConfigMap with Data named %s and for namespace %s",
			createdConfigMapBuilderWithData.Object.Name, createdConfigMapBuilderWithData.Object.Namespace)

		return nil, err
	}

	glog.V(gpuparams.GpuLogLevel).Infof(
		"Created ConfigMap with Data named %s and for namespace %s",
		createdConfigMapBuilderWithData.Object.Name, createdConfigMapBuilderWithData.Object.Namespace)

	return createdConfigMapBuilderWithData.Object, nil
}

// CreateCUDASamplePod returns a Pod after it is Ready after a timeout period.
func CreateCUDASamplePod(apiClient *clients.Settings, podName, podNamespace string,
	cudaSampleImage string, timeout time.Duration) (*corev1.Pod, error) {
	var volumeDefaultMode int32 = 0777

	configMapVolumeSource := &corev1.ConfigMapVolumeSource{}
	configMapVolumeSource.Name = "cuda-sample-entrypoint"
	configMapVolumeSource.DefaultMode = &volumeDefaultMode

	var err error = nil

	return &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      podName,
			Namespace: podNamespace,
			Labels: map[string]string{
				"app": "cuda-sample-app",
			},
		},
		Spec: corev1.PodSpec{
			RestartPolicy: corev1.RestartPolicyNever,
			SecurityContext: &corev1.PodSecurityContext{
				RunAsNonRoot:   &isTrue,
				SeccompProfile: &corev1.SeccompProfile{Type: "RuntimeDefault"},
			},
			Tolerations: []corev1.Toleration{
				{
					Operator: corev1.TolerationOpExists,
				},
				{
					Key:      "nvidia.com/gpu",
					Effect:   corev1.TaintEffectNoSchedule,
					Operator: corev1.TolerationOpExists,
				},
			},
			Containers: []corev1.Container{
				{
					Image:           cudaSampleImage,
					ImagePullPolicy: corev1.PullIfNotPresent,
					SecurityContext: &corev1.SecurityContext{
						AllowPrivilegeEscalation: &isFalse,
						Capabilities: &corev1.Capabilities{
							Drop: []corev1.Capability{
								"ALL",
							},
						},
					},
					Name: "cuda-sample-ctr",
					Command: []string{
						"/bin/entrypoint.sh",
					},
					Resources: corev1.ResourceRequirements{
						Limits: corev1.ResourceList{
							"nvidia.com/gpu": resource.MustParse("1"),
						},
					},
					VolumeMounts: []corev1.VolumeMount{
						{
							Name:      "entrypoint",
							MountPath: "/bin/entrypoint.sh",
							ReadOnly:  true,
							SubPath:   "entrypoint.sh",
						},
					},
				},
			},
			Volumes: []corev1.Volume{
				{
					Name: "entrypoint",
					VolumeSource: corev1.VolumeSource{
						ConfigMap: configMapVolumeSource,
					},
				},
			},
			NodeSelector: map[string]string{
				"nvidia.com/gpu.present":         "true",
				"node-role.kubernetes.io/worker": "",
			},
		},
	}, err
}
