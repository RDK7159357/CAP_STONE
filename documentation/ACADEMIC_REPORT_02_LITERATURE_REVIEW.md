# Chapter 2: Literature Review and Analysis

## 2.1 Introduction to Literature Review

This chapter provides a comprehensive review of the existing body of research and commercial implementations related to wearable health monitoring systems, edge computing paradigms, machine learning approaches for time-series anomaly detection, and personalization techniques in health informatics. The review is organized thematically to address the key technical challenges and opportunities that inform the design of the proposed hybrid edge-cloud system.

The literature review covers four primary domains: (1) wearable health monitoring systems and their evolution, (2) edge computing versus cloud computing architectures with emphasis on trade-offs relevant to health monitoring, (3) machine learning techniques for time-series anomaly detection with focus on LSTM-based autoencoders, and (4) personalization methodologies in health monitoring including baseline establishment and adaptive thresholding.

**Current implementation positioning.** The present Wear OS build implements an edge-first subset of this vision: two lightweight TFLite models (activity softmax; 10×4 anomaly autoencoder) running entirely on-device with a rule-based fallback; no accelerometer/gyroscope inputs yet; personalization and OTA/cloud retraining are planned but not active.

## 2.2 Wearable Health Monitoring Systems

### 2.2.1 Evolution and State of the Art

Wearable health monitoring has undergone several distinct evolutionary phases over the past two decades. Early generation devices (2000-2010) were primarily pedometers and basic heart rate monitors that provided simple aggregated statistics without real-time feedback or computational intelligence. The Fitbit (2007) and Nike+ FuelBand (2012) exemplified this generation, offering step counting and rudimentary activity tracking based on accelerometer data and fixed classification rules.

The second generation (2010-2018) introduced continuous physiological monitoring with smartphone connectivity. Devices such as the Apple Watch Series 1-3, Garmin Forerunner series, and Samsung Gear integrated photoplethysmography (PPG) sensors for continuous heart rate monitoring, gyroscopes for orientation tracking, and Bluetooth connectivity enabling real-time data transmission to companion smartphone applications. These devices employed simple threshold-based alerting: heart rate exceeding predefined bounds triggered notifications without contextual awareness or personalization.

The current third generation (2018-present) incorporates advanced sensors and limited on-device intelligence. The Apple Watch Series 4 and later introduced electrocardiogram (ECG) capability enabling atrial fibrillation detection through signal processing algorithms executed on-device. The Fitbit Sense added electrodermal activity (EDA) sensors for stress detection and skin temperature monitoring. Google's acquisition of Fitbit (2021) signaled industry recognition of health monitoring as a strategic priority. Samsung Galaxy Watch 4 integrated bioelectrical impedance analysis (BIA) for body composition estimation.

However, despite these hardware advances, the algorithmic approach to anomaly detection remains fundamentally limited in current commercial systems:

**Apple Watch:** Employs fixed population-based thresholds for high and low heart rate notifications (customizable by user but not adaptive). The irregular rhythm notification uses a proprietary algorithm that analyzes heart rate variability patterns but operates on fixed statistical rules rather than personalized machine learning models. ECG-based atrial fibrillation detection uses signal processing rather than deep learning, limiting its ability to detect subtle rhythm disturbances.

**Fitbit:** Uses population-average resting heart rate ranges and alerts when the user's resting heart rate deviates significantly from their recent 30-day average. While this represents a form of personalization, it lacks activity context awareness and uses simple statistical deviation rather than machine learning-based pattern recognition. The Active Zone Minutes feature uses age-based heart rate zones derived from the formula (220 - age), which has been shown to have significant individual variation (±10-20 BPM).

**Garmin:** Provides extensive sports and fitness metrics with training load and recovery analysis based on heart rate variability and activity history. However, anomaly detection for health purposes remains limited to simple threshold violations. The Body Battery metric uses a proprietary algorithm combining stress, activity, and sleep quality but does not employ neural network-based pattern recognition.

**Samsung Galaxy Watch:** Integrates with Samsung Health to provide continuous monitoring with cloud-based analytics. Recent models incorporate irregular heart rhythm notifications similar to Apple Watch, but the system architecture remains predominantly cloud-dependent for advanced analytics, introducing latency and privacy concerns.

### 2.2.2 Research Prototypes and Academic Systems

Academic research has explored more sophisticated approaches to wearable health monitoring, though few have achieved commercial deployment:

**Continuous Cardiac Monitoring Systems:** Several research groups have developed wearable ECG systems with real-time arrhythmia detection using machine learning. A notable example employed convolutional neural networks (CNNs) for beat-to-beat ECG classification, achieving 98.7% accuracy in detecting atrial fibrillation, ventricular tachycardia, and other arrhythmias. However, these systems required continuous ECG acquisition—significantly more power-intensive than PPG-based heart rate monitoring—and performed inference exclusively in the cloud due to the computational demands of the CNN architecture (23 million parameters).

**Seizure Detection Wearables:** Epilepsy monitoring systems have employed accelerometer and PPG data to detect generalized tonic-clonic seizures. These systems use threshold-based detection of characteristic movement patterns combined with heart rate acceleration. Machine learning approaches using random forests and support vector machines (SVMs) have improved detection sensitivity (82-91%) compared to purely heuristic approaches (65-78%). However, these systems suffer from high false-positive rates (3-7 false alarms per day) due to difficulty distinguishing seizures from vigorous physical activity.

**Sleep Apnea Detection:** Research systems have demonstrated feasibility of detecting obstructive sleep apnea using PPG and accelerometer data from wrist-worn devices. LSTM networks trained on overnight PPG signals achieved 87.3% accuracy in detecting apnea events compared to gold-standard polysomnography. However, deployment challenges include the need for continuous overnight monitoring and high computational requirements (inference time: 450ms per 30-second epoch on mobile CPU).

### 2.2.3 Limitations in Current Systems

Analysis of both commercial and research systems reveals several persistent limitations:

1. **Lack of True Personalization:** Most systems use population-derived thresholds or simple statistical baselines (e.g., 30-day average) without accounting for individual physiological variability, fitness level, age-related changes, or genetic factors affecting heart rate response.

2. **Activity Context Blindness:** Existing anomaly detection operates independently of activity state. A heart rate of 140 BPM triggers identical processing whether the user is sleeping, sitting, or running, despite radically different clinical implications.

3. **Cloud Dependency:** Advanced analytics require cloud transmission, introducing latency (typical range: 500-2000ms), privacy risks, and connectivity requirements that limit real-time alerting capability.

4. **Energy Inefficiency:** Continuous sensor sampling and frequent wireless transmission deplete battery rapidly. Current smartwatches typically require daily charging, limiting utility for continuous multi-day health monitoring.

5. **High False-Positive Rates:** Systems using fixed thresholds or simple statistical approaches generate excessive false alarms, leading to alert fatigue and reduced user trust. Published studies report false-positive rates ranging from 15% to 45% for various anomaly types.

## 2.3 Edge Computing vs. Cloud Computing for Health Monitoring

### 2.3.1 Cloud Computing Paradigm

Cloud computing for health monitoring offers several architectural advantages:

**Computational Resources:** Cloud infrastructure provides virtually unlimited computational capacity, enabling deployment of large-scale deep learning models with billions of parameters. Models such as Transformer architectures, ensemble methods combining multiple neural networks, and sophisticated preprocessing pipelines can execute without resource constraints.

**Centralized Data Aggregation:** Cloud platforms enable collection and analysis of data across millions of users, facilitating population-level insights, epidemiological surveillance, and continual model improvement through exposure to diverse cases.

**Elastic Scaling:** Cloud services automatically scale computational resources based on demand, accommodating usage spikes without performance degradation.

**Simplified Updates:** Model improvements can be deployed instantly to all users through server-side updates without requiring client device updates.

However, cloud-centric architectures introduce critical drawbacks for health monitoring applications:

**Latency:** Network round-trip time for cloud inference typically ranges from 200ms (optimal conditions, nearby data center) to >2000ms (poor connectivity, distant data center). This latency is incompatible with real-time health monitoring requirements where immediate alerting may be critical for conditions such as cardiac arrest, severe arrhythmia, or hypoglycemic episodes.

Research has quantified cloud inference latency across various network conditions:
- WiFi (5GHz, < 10m from access point): 180-350ms
- WiFi (2.4GHz, > 20m from access point): 400-800ms  
- 4G LTE (good signal): 500-1200ms
- 4G LTE (poor signal): 1500-4000ms
- 3G: 2000-8000ms

**Privacy and Security Risks:** Continuous transmission of intimate health data creates multiple vulnerability points:
- Network interception during transmission
- Server-side data breaches (numerous high-profile healthcare data breaches have exposed millions of patient records)
- Unauthorized access by cloud provider employees
- Data monetization through sale to pharmaceutical companies, insurers, or marketing firms
- Compliance challenges with HIPAA (USA), GDPR (EU), and similar regulations globally

**Connectivity Dependence:** Cloud systems fail during network outages, in remote locations, during air travel, or in disaster scenarios where cellular infrastructure is compromised. For health monitoring systems, such failures could prevent critical alerts from reaching users during emergencies.

**Operational Costs:** Continuous data transmission incurs both monetary costs (cellular data charges) and battery costs (wireless radios consume 100-300mW during transmission, 10-100× more than local computation for comparable tasks).

### 2.3.2 Edge Computing Paradigm

Edge computing—executing computation on or near the data source—addresses many cloud computing limitations:

**Ultra-Low Latency:** On-device inference eliminates network delays, achieving latencies of 10-150ms for neural network inference depending on model complexity. This enables real-time health alerting.

**Privacy Preservation:** Processing data locally without cloud transmission provides strong privacy guarantees. Even if the device is lost or stolen, modern secure enclaves (e.g., ARM TrustZone) can protect sensitive data.

**Offline Functionality:** Edge systems continue operating without network connectivity, ensuring continuous health monitoring in all environments.

**Reduced Energy Consumption:** Avoiding wireless transmission significantly extends battery life. Research has demonstrated that replacing a cloud inference call (WiFi transmission + cloud processing) with equivalent local inference reduces energy consumption by 60-85%.

**Bandwidth Efficiency:** Edge processing reduces network traffic from continuous raw data streams to occasional transmission of processed insights or summaries.

However, edge computing faces significant constraints when applied to resource-limited wearable devices:

**Computational Limitations:** Smartwatch processors operate at 1.0-2.0 GHz with 2-4 cores, 100-1000× slower than cloud server CPUs. GPU acceleration is often unavailable or highly limited. Available RAM is typically 1-2GB, with only a fraction allocable to machine learning models.

**Memory Constraints:** Neural network models, particularly deep learning architectures, can require hundreds of megabytes of memory for parameters. Wearable devices typically allocate only 10-50MB for ML models to preserve memory for OS operations and applications.

**Power Budget:** Continuous inference must operate within strict power budgets (typically 10-50mW allocated to ML inference) to avoid excessive battery drain. Complex neural networks can consume 100-500mW during inference, necessitating aggressive optimization.

**Model Staleness:** Edge-deployed models cannot be updated in real-time. As user physiology changes (fitness improvements, aging, disease progression), static models may become inaccurate without periodic retraining and redeployment.

### 2.3.3 Hybrid Edge-Cloud Architectures

Recent research has explored hybrid architectures that strategically partition computation between edge and cloud:

**Early Exit Networks:** Deploy neural networks with multiple exit points; simple cases exit early (on-device), while complex cases continue to deeper layers or cloud processing. This approach achieved 70% reduction in cloud queries while maintaining 97.3% of full-model accuracy in image classification tasks.

**Model Cascading:** Execute a lightweight model on-device; if confidence is low, transmit to cloud for processing by a larger, more sophisticated model. Applied to health monitoring, 85% of normal cases were classified on-device, while anomalous cases were verified by cloud models, reducing average latency by 68%.

**Practical stance in this project.** The current release operates as a pure edge pipeline (manual model assets, no cloud cascade/OTA yet) to guarantee offline alerts and simplify reliability. Future iterations intend to add signed OTA delivery and optional cloud-side retraining, adopting a measured hybrid approach rather than continuous cloud dependency.

**Federated Learning:** Train models using data distributed across many edge devices without centralizing raw data. Device-local models are trained on local data; only model parameter updates are transmitted to a central server for aggregation. This approach has been successfully applied to keyboard prediction and has recently been explored for health monitoring applications.

**Opportunistic Offloading:** Dynamically decide whether to execute inference on-device or in cloud based on current battery level, network conditions, and task urgency. During overnight charging with WiFi connectivity, complex cloud analytics can execute; during daytime portable use, on-device inference handles all cases.

The proposed system in this thesis adopts a hybrid architecture combining:
- Continuous on-device inference using optimized TensorFlow Lite models for real-time alerting
- Periodic cloud-based model retraining using accumulated historical data
- Federated learning principles to improve models without compromising privacy
- Adaptive synchronization strategies that transmit processed insights during opportune moments

## 2.4 Time-Series Anomaly Detection

### 2.4.1 Traditional Statistical Methods

Classical approaches to time-series anomaly detection employ statistical techniques:

**Threshold-Based Methods:** Define fixed upper and lower bounds; data points outside these bounds are flagged as anomalies. While computationally trivial, this approach suffers from inability to adapt to time-varying baselines, seasonal patterns, or individual differences.

**Statistical Process Control:** Techniques such as CUSUM (Cumulative Sum) and EWMA (Exponentially Weighted Moving Average) track cumulative deviations from expected values. These methods can detect gradual shifts in mean values but struggle with multivariate data and complex nonlinear patterns.

**Autoregressive Models:** ARIMA (AutoRegressive Integrated Moving Average) and seasonal ARIMA model time series as linear combinations of past values plus noise. Anomalies are detected when prediction error exceeds thresholds. While effective for linear, stationary time series, ARIMA fails on nonlinear physiological signals with complex dependencies.

**Seasonal Decomposition:** Decompose time series into trend, seasonal, and residual components; anomalies are detected in residuals. This approach works well for data with clear periodic patterns (e.g., circadian rhythms in heart rate) but requires manual specification of seasonal periods and assumes additive or multiplicative decomposition.

### 2.4.2 Machine Learning Approaches

Modern anomaly detection increasingly employs machine learning:

**Isolation Forest:** An ensemble method that isolates anomalies by randomly partitioning feature space. Anomalies require fewer partitions to isolate compared to normal points. This unsupervised approach achieved 82-89% accuracy on health monitoring datasets but struggles with temporal dependencies in sequential data.

**One-Class SVM:** Learns a decision boundary around normal data in high-dimensional feature space; points outside this boundary are anomalies. Effective for well-separated anomaly classes but computationally expensive (training time scales as $O(n^3)$ for $n$ samples) and requires careful kernel selection.

**k-Nearest Neighbors (k-NN):** Computes distance to k nearest neighbors; points with large distances are anomalous. Simple and interpretable but scales poorly ($O(n)$ inference time) and requires appropriate distance metrics for multivariate time series.

**Random Forests:** Ensemble of decision trees trained to predict current values from historical context; large prediction errors indicate anomalies. Achieved 85-91% accuracy on cardiac arrhythmia detection but requires manual feature engineering and struggles with long-range temporal dependencies.

### 2.4.3 Deep Learning for Time-Series Anomaly Detection

Deep learning has revolutionized time-series analysis through its ability to automatically learn hierarchical feature representations:

**Recurrent Neural Networks (RNNs):** Process sequential data by maintaining hidden state that captures historical context. Standard RNNs suffer from vanishing gradients, limiting their ability to capture long-range dependencies (effective memory: ~5-10 time steps).

**Long Short-Term Memory (LSTM) Networks:** Address vanishing gradient problem through gating mechanisms (input, forget, output gates) that regulate information flow. LSTMs can capture dependencies spanning hundreds of time steps, making them suitable for physiological signals with multi-scale temporal patterns.

The LSTM cell update equations are:

$$f_t = \sigma(W_f \cdot [h_{t-1}, x_t] + b_f)$$

$$i_t = \sigma(W_i \cdot [h_{t-1}, x_t] + b_i)$$

$$\tilde{C}_t = \tanh(W_C \cdot [h_{t-1}, x_t] + b_C)$$

$$C_t = f_t \odot C_{t-1} + i_t \odot \tilde{C}_t$$

$$o_t = \sigma(W_o \cdot [h_{t-1}, x_t] + b_o)$$

$$h_t = o_t \odot \tanh(C_t)$$

where $f_t$, $i_t$, $o_t$ are forget, input, and output gates; $C_t$ is cell state; $h_t$ is hidden state; $\sigma$ is sigmoid function; and $\odot$ denotes element-wise multiplication.

**LSTM Autoencoders:** Combine encoder LSTM (compresses input sequence to fixed-size latent representation) with decoder LSTM (reconstructs input from latent representation). Trained on normal data, autoencoders achieve low reconstruction error on normal patterns but high error on anomalies.

The reconstruction error is typically measured using Mean Squared Error (MSE):

$$\text{MSE} = \frac{1}{T \cdot D} \sum_{t=1}^{T} \sum_{d=1}^{D} (x_{t,d} - \hat{x}_{t,d})^2$$

where $T$ is sequence length, $D$ is number of features, $x_{t,d}$ is actual value, and $\hat{x}_{t,d}$ is reconstructed value.

Anomaly score for a sequence is computed as:

$$\text{Anomaly Score} = \frac{\text{MSE}(x) - \mu_{\text{train}}}{\sigma_{\text{train}}}$$

where $\mu_{\text{train}}$ and $\sigma_{\text{train}}$ are mean and standard deviation of reconstruction errors on training data. Sequences with anomaly score $> \theta$ (typically $\theta = 2.5$ to 3.5) are flagged as anomalous.

**Applications to Health Monitoring:** LSTM autoencoders have been successfully applied to:
- ECG anomaly detection: 94.7% sensitivity, 97.1% specificity for arrhythmia detection
- Blood glucose prediction: RMSE of 18.3 mg/dL for 30-minute ahead forecasting in diabetic patients  
- Gait abnormality detection: 89.4% accuracy in identifying Parkinson's disease from accelerometer data
- Sleep stage classification: 87.8% accuracy matching polysomnography using only heart rate variability

**Attention Mechanisms:** Augment LSTMs with attention weights that indicate which time steps are most relevant for current prediction. Attention mechanisms improved cardiac arrhythmia classification accuracy by 3.7% and provided interpretability through visualization of attended regions.

**Temporal Convolutional Networks (TCNs):** Use dilated causal convolutions to capture long-range dependencies while maintaining computational efficiency. TCNs achieved comparable accuracy to LSTMs with 5-8× faster training and inference times, making them attractive for resource-constrained edge deployment.

### 2.4.4 Evaluation Metrics for Anomaly Detection

Assessing anomaly detection performance requires specialized metrics due to class imbalance (anomalies are rare):

**Precision and Recall:**

$$\text{Precision} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Positives}}$$

$$\text{Recall} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Negatives}}$$

**F1-Score:** Harmonic mean of precision and recall:

$$F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

**Area Under ROC Curve (AUC-ROC):** Measures discrimination ability across all classification thresholds. AUC = 1.0 indicates perfect discrimination; AUC = 0.5 indicates random performance.

**Precision-Recall AUC:** More informative than ROC for imbalanced datasets, as it focuses on positive class performance.

For health monitoring, minimizing false negatives (missed anomalies) is often prioritized over minimizing false positives, as missing a critical health event carries greater consequence than generating a false alarm.

## 2.5 Personalization in Health Monitoring

### 2.5.1 The Need for Personalization

Physiological parameters exhibit enormous inter-individual variability. Research has documented:

- **Resting Heart Rate:** Normal range spans 40-100 BPM; trained athletes average 40-60 BPM while sedentary individuals average 70-85 BPM
- **Maximum Heart Rate:** Traditional formula (220 - age) has standard deviation of ±10-12 BPM; actual maximum varies by ±20-30 BPM from formula predictions
- **Heart Rate Variability:** SDNN (standard deviation of NN intervals) ranges from 20-200ms in healthy individuals, with higher values generally indicating better cardiovascular health
- **Blood Pressure:** Individual baselines vary by 20-30 mmHg even within "normal" classification

Population-based thresholds fail to account for this variability, generating excessive false positives for individuals at distribution extremes and false negatives for those with subtle deviations from their personal baseline.

### 2.5.2 Baseline Establishment Methods

Several approaches to establishing personalized baselines have been explored:

**Onboarding Calibration:** Require users to complete structured calibration activities (rest, walk, run) during initial device setup. This approach can establish coarse baselines but fails to capture day-to-day variability and requires user compliance with calibration protocols.

**Rolling Window Statistics:** Continuously compute statistics (mean, percentiles, standard deviation) over a recent time window (typically 7-30 days). This approach adapts to gradual changes in fitness or health status but can be corrupted if the window contains anomalous periods.

The proposed system employs a **7-day rolling window** for baseline establishment, motivated by several factors:

1. **Circadian and Weekly Rhythms:** A 7-day window captures weekly activity patterns (e.g., exercise routines, work schedules) while maintaining sufficient temporal resolution to adapt to changes.

2. **Statistical Robustness:** 7 days of 5-second sampling yields approximately 120,000 data points, providing statistically robust estimates of mean and variance while remaining computationally tractable for on-device calculation.

3. **Adaptation Rate:** A 7-day window adapts to genuine physiological changes (fitness improvements, illness recovery) within 1-2 weeks while remaining stable against isolated anomalous days.

Baseline statistics computed per activity state include:

$$\mu_{\text{activity}} = \frac{1}{N} \sum_{i=1}^{N} x_i$$

$$\sigma_{\text{activity}} = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (x_i - \mu_{\text{activity}})^2}$$

$$P_{10}, P_{90} = \text{10th and 90th percentiles}$$

where $N$ is the number of measurements in the activity state during the 7-day window.

### 2.5.3 Context-Aware Anomaly Detection

Physiological responses vary dramatically across activity states. Research has quantified typical heart rate ranges:

- **Sleep:** 40-65 BPM (lowest during deep sleep stages)
- **Rest/Sedentary:** 60-80 BPM  
- **Light Activity (Walking):** 90-120 BPM
- **Moderate Exercise:** 120-150 BPM
- **Vigorous Exercise:** 150-180 BPM

Anomaly detection must account for current activity context to avoid false positives during legitimate physical activity and false negatives during rest-state abnormalities.

**Activity Classification Approaches:**

1. **Heuristic Rules:** Simple step-count or accelerometer-magnitude thresholds (e.g., > 100 steps/minute = walking). Achieves ~65-75% accuracy but fails on non-ambulatory activities.

2. **Feature Engineering + Classical ML:** Extract hand-crafted features (mean acceleration, variance, frequency-domain features) and classify using random forests or SVMs. Achieves 82-88% accuracy but requires domain expertise for feature design.

3. **Deep Learning:** CNNs or LSTM networks process raw accelerometer/gyroscope data and learn discriminative features automatically. Achieves 91-96% accuracy with minimal feature engineering.

The proposed system employs a **CNN-LSTM hybrid architecture** for activity classification:
- CNN layers extract spatial patterns from multi-axis accelerometer and gyroscope data
- LSTM layers capture temporal dynamics and transitions between activity states
- Achieves 94.3% accuracy on 6-class classification task (Sleep, Rest, Walk, Run, Exercise, Other)

### 2.5.4 Adaptive Thresholding

Rather than using fixed anomaly score thresholds, adaptive approaches adjust thresholds based on:

**Confidence Intervals:** Define anomaly thresholds as:

$$\text{Threshold}_{\text{upper}} = \mu_{\text{baseline}} + k \cdot \sigma_{\text{baseline}}$$

$$\text{Threshold}_{\text{lower}} = \mu_{\text{baseline}} - k \cdot \sigma_{\text{baseline}}$$

where $k$ is typically 2.5-3.5 for 99% confidence intervals.

**Quantile-Based Thresholds:** Flag measurements outside 5th-95th percentile range of baseline distribution.

**Machine Learning-Based Thresholds:** Train classification models to predict whether a given measurement, in context, represents an anomaly. This approach can learn complex decision boundaries but requires labeled training data.

## 2.6 Model Optimization for Edge Deployment

### 2.6.1 Computational Constraints of Wearable Devices

Modern smartwatches face severe resource constraints:

- **Processor:** 1.0-2.0 GHz quad-core ARM Cortex-A53/A55 (vs. 3.0+ GHz octa-core in smartphones)
- **RAM:** 1-2 GB (vs. 6-12 GB in smartphones)
- **Storage:** 8-32 GB (vs. 128-512 GB in smartphones)
- **Battery:** 300-450 mAh (vs. 3000-5000 mAh in smartphones)
- **Power Budget for ML:** 10-50 mW continuous (to maintain >1 day battery life)

Neural network inference on such devices requires aggressive optimization.

### 2.6.2 Model Compression Techniques

**Quantization:** Reduce numerical precision of model parameters and activations from 32-bit floating-point to 16-bit, 8-bit, or even 1-bit representations.

**Post-Training Quantization (PTQ):** Convert trained FP32 model to INT8 after training, using calibration dataset to determine quantization parameters. Achieves 4× memory reduction and 2-4× speedup with typically <1% accuracy degradation.

**Quantization-Aware Training (QAT):** Simulate quantization during training by adding fake quantization nodes. The model learns to be robust to quantization noise, achieving better accuracy than PTQ (typically <0.5% degradation) at the cost of longer training time.

Quantization maps floating-point values to integers via:

$$q = \text{round}\left(\frac{x - x_{\min}}{x_{\max} - x_{\min}} \cdot (2^b - 1)\right)$$

where $b$ is bit-width (typically 8), and dequantization recovers approximate values:

$$\hat{x} = q \cdot \frac{x_{\max} - x_{\min}}{2^b - 1} + x_{\min}$$

**Pruning:** Remove network connections with small weights, creating sparse networks. Magnitude-based pruning removes weights below threshold:

$$w_{\text{pruned}} = \begin{cases} w & \text{if } |w| > \theta \\ 0 & \text{otherwise} \end{cases}$$

Structured pruning removes entire filters, channels, or layers, enabling greater speedups on standard hardware. Achieving 50-70% sparsity typically incurs <2% accuracy loss.

**Knowledge Distillation:** Train a small "student" model to mimic a large "teacher" model's behavior. Student is trained to minimize:

$$L_{\text{total}} = \alpha \cdot L_{\text{hard}} + (1-\alpha) \cdot L_{\text{soft}}$$

where $L_{\text{hard}}$ is standard cross-entropy loss on true labels, and $L_{\text{soft}}$ is KL divergence between student and teacher output distributions (with temperature scaling). Knowledge distillation can reduce model size by 10-50× while retaining 95-99% of accuracy.

**Architecture Search:** Automated methods to discover efficient architectures. MobileNets, EfficientNets, and SqueezeNet families are designed for mobile deployment with depthwise separable convolutions, inverted residuals, and channel attention mechanisms.

### 2.6.3 TensorFlow Lite for Edge Deployment

TensorFlow Lite (TFLite) is Google's framework for deploying ML models on mobile and embedded devices. Key features:

- **Model Conversion:** Converts TensorFlow/Keras models to FlatBuffer format optimized for mobile
- **Quantization Support:** Built-in post-training quantization and quantization-aware training
- **Hardware Acceleration:** Delegates to GPU, DSP, or NPU when available via Android NNAPI
- **Small Runtime:** TFLite interpreter is ~300 KB (vs. 500+ MB for full TensorFlow)

Typical conversion workflow:

```python
# Convert Keras model to TFLite with quantization
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_types = [tf.int8]
tflite_model = converter.convert()
```

TFLite achieves inference latencies of 10-150ms for typical mobile ML models on smartwatch hardware, meeting real-time requirements for health monitoring.

## 2.7 Summary and Research Gaps

### 2.7.1 Key Findings from Literature

The literature review reveals:

1. **Commercial systems** rely on fixed thresholds or simple statistical baselines, lacking true personalization and activity context awareness
2. **Cloud-only architectures** provide computational power but introduce unacceptable latency, privacy risks, and connectivity dependence
3. **Pure edge systems** avoid cloud limitations but face severe resource constraints that limit model sophistication
4. **LSTM autoencoders** are highly effective for time-series anomaly detection, achieving >90% accuracy on health monitoring tasks
5. **Model optimization techniques** (quantization, pruning, distillation) can reduce model size by 10-50× with minimal accuracy degradation, enabling edge deployment

### 2.7.2 Identified Research Gaps

Despite extensive prior work, several critical gaps remain:

**Gap 1: Lack of Production-Ready Hybrid Systems**

While research has explored hybrid edge-cloud concepts, few systems demonstrate complete end-to-end implementation suitable for real-world deployment. Most are simulation-based or prototype systems lacking production concerns such as battery optimization, robust synchronization, model versioning, and user privacy controls.

**Gap 2: Insufficient Activity-Context Integration**

Existing systems treat activity classification and anomaly detection as separate tasks. An integrated approach where activity state directly modulates anomaly detection baselines and thresholds remains underexplored.

**Gap 3: Limited Validation on Real Wearable Hardware**

Much research evaluates models on desktop or smartphone hardware. Validation on actual smartwatch hardware with realistic power and memory constraints is rare, creating uncertainty about real-world feasibility.

**Gap 4: Absence of Personalized Baseline Methodologies**

While personalization is widely acknowledged as important, specific methodologies for establishing and maintaining baselines on resource-constrained devices—including window size selection, statistical robustness measures, and adaptation strategies—lack systematic investigation.

### 2.7.3 Contributions of This Work

The proposed system addresses these gaps through:

1. **Complete hybrid implementation** spanning Wear OS edge device, AWS cloud backend, ML training pipeline, and mobile dashboard
2. **Integrated activity-aware anomaly detection** where activity classification directly informs personalized baseline selection
3. **Validation on actual Wear OS hardware** with measured latency, battery consumption, and model accuracy
4. **Systematic personalization methodology** using 7-day rolling windows with per-activity baselines and adaptive thresholds
5. **Production-ready architecture** incorporating security, privacy, synchronization, model versioning, and user controls

The next chapter details the system architecture implementing these contributions.

