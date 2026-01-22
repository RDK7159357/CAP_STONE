# Architecture Diagrams - Mermaid.js Code

## Diagram 1: Overall System Architecture (Hybrid Edge-Cloud)

```mermaid
graph TB
    subgraph "Wear OS Watch - Edge Computing"
        A[Health Sensors] --> B[Sensor Data Collection]
        B --> C[Health Services API]
        C --> D[Raw Data<br/>HR, SpO2, Accel, Gyro]
        D --> E[TFLite Activity Classifier<br/>50ms inference]
        D --> F[Personal Baseline Engine<br/>7-day window]
        E --> G[Activity State<br/>Sleep/Rest/Walk/Run/Exercise]
        G --> H[TFLite Anomaly Detector<br/>LSTM - 92ms inference]
        F --> H
        H --> I{Anomaly<br/>Detected?}
        I -->|Yes| J[Instant Alert<br/>Notification]
        I -->|No| K[Room Database<br/>Local Storage]
        J --> K
    end
    
    subgraph "Cloud Backend - AWS"
        L[API Gateway<br/>REST API]
        M[Lambda Function<br/>Data Ingestion]
        N[DynamoDB<br/>Time-series Storage]
        O[DynamoDB Streams]
        P[SageMaker<br/>ML Training]
        Q[S3 Model Registry<br/>Versioning]
        R[Lambda Deploy<br/>Model Push]
    end
    
    subgraph "Mobile Dashboard - React Native + Expo"
        S[Dashboard UI]
        T[Historical Charts]
        U[Personal Insights]
        V[Alert History]
    end
    
    K -->|Periodic Sync<br/>Every 30 min| L
    L --> M
    M --> N
    N --> O
    O --> P
    P -->|Train Advanced Models| Q
    Q -->|TFLite Conversion| R
    R -->|OTA Update| E
    R -->|OTA Update| H
    N --> S
    S --> T
    S --> U
    S --> V
    
    style A fill:#e1f5ff
    style E fill:#ffe1e1
    style H fill:#ffe1e1
    style J fill:#ffcccc
    style P fill:#e1ffe1
    style Q fill:#e1ffe1
```

---

## Diagram 2: Data Flow Architecture

```mermaid
flowchart TD
    Start([Start: Sensor Reading]) --> Collect[Collect Sensor Data<br/>HR, Accel, Gyro<br/>Every 5 seconds]
    
    Collect --> PreProcess[Preprocessing<br/>Normalize & Window<br/>100 samples buffer]
    
    PreProcess --> Activity[Activity Classification<br/>TFLite CNN-LSTM Model]
    
    Activity --> State{Activity<br/>State}
    
    State -->|Sleep| Baseline1[Personal Baseline<br/>Sleep: HR 45-60 BPM]
    State -->|Rest| Baseline2[Personal Baseline<br/>Rest: HR 60-80 BPM]
    State -->|Walk| Baseline3[Personal Baseline<br/>Walk: HR 90-120 BPM]
    State -->|Run| Baseline4[Personal Baseline<br/>Run: HR 130-170 BPM]
    State -->|Exercise| Baseline5[Personal Baseline<br/>Exercise: HR 140-180 BPM]
    State -->|Other| Baseline6[Personal Baseline<br/>Other: HR 70-100 BPM]
    
    Baseline1 --> Anomaly[LSTM Anomaly Detector<br/>Compare: Current vs Baseline]
    Baseline2 --> Anomaly
    Baseline3 --> Anomaly
    Baseline4 --> Anomaly
    Baseline5 --> Anomaly
    Baseline6 --> Anomaly
    
    Anomaly --> Score{Anomaly<br/>Score}
    
    Score -->|> 0.8| Critical[Critical Alert<br/>Immediate Notification]
    Score -->|0.6-0.8| Warning[Warning Alert<br/>Monitor Closely]
    Score -->|< 0.6| Normal[Normal<br/>No Action]
    
    Critical --> Store[Store in Room DB<br/>Local SQLite]
    Warning --> Store
    Normal --> Store
    
    Store --> Sync{Cloud<br/>Sync?}
    
    Sync -->|Every 30 min<br/>or WiFi| Cloud[Upload to Cloud<br/>API Gateway → DynamoDB]
    Sync -->|Offline| Queue[Queue for Later<br/>WorkManager]
    
    Cloud --> Train[Weekly ML Training<br/>SageMaker LSTM]
    Train --> Optimize[Model Optimization<br/>Quantization + Pruning]
    Optimize --> Deploy[Deploy TFLite<br/>to Edge Devices]
    Deploy --> Activity
    
    Queue --> Cloud
    
    style Critical fill:#ff6b6b
    style Warning fill:#ffa500
    style Normal fill:#90ee90
    style Activity fill:#87ceeb
    style Anomaly fill:#87ceeb
```

---

## Diagram 3: ML Pipeline Architecture

```mermaid
graph LR
    subgraph "Data Collection Layer"
        A1[Wear OS Sensors] --> A2[Raw Data Stream]
        A2 --> A3[Local Preprocessing]
        A3 --> A4[Room Database]
    end
    
    subgraph "Edge ML Layer - TensorFlow Lite"
        B1[Activity Classifier<br/>CNN-LSTM]
        B2[Anomaly Detector<br/>LSTM Autoencoder]
        B3[Baseline Calculator<br/>Statistical Engine]
        
        A4 --> B1
        A4 --> B3
        B1 --> B2
        B3 --> B2
    end
    
    subgraph "Cloud Storage Layer"
        C1[API Gateway]
        C2[Lambda Ingestion]
        C3[DynamoDB<br/>Time-series Data]
        C4[S3<br/>Raw Data Archive]
        
        A4 -->|Periodic Sync| C1
        C1 --> C2
        C2 --> C3
        C2 --> C4
    end
    
    subgraph "Cloud ML Training Layer"
        D1[SageMaker Training<br/>GPU Instances]
        D2[LSTM Autoencoder<br/>Full Model]
        D3[Activity Classifier<br/>Deep CNN-LSTM]
        D4[Hyperparameter Tuning<br/>Optuna]
        
        C3 --> D1
        D1 --> D2
        D1 --> D3
        D1 --> D4
    end
    
    subgraph "Model Optimization Layer"
        E1[Post-training Quantization<br/>FP32 → INT8]
        E2[Weight Pruning<br/>60% sparsity]
        E3[Layer Fusion<br/>Operator Optimization]
        E4[TFLite Conversion]
        
        D2 --> E1
        D3 --> E1
        E1 --> E2
        E2 --> E3
        E3 --> E4
    end
    
    subgraph "Model Deployment Layer"
        F1[Model Registry<br/>S3 + Versioning]
        F2[A/B Testing<br/>Gradual Rollout]
        F3[OTA Update<br/>Push to Devices]
        
        E4 --> F1
        F1 --> F2
        F2 --> F3
        F3 --> B1
        F3 --> B2
    end
    
    subgraph "Analytics Layer"
        G1[Dashboard API]
        G2[React Native Mobile App]
        G3[Web Dashboard]
        
        C3 --> G1
        G1 --> G2
        G1 --> G3
    end
    
    style B1 fill:#ffe1e1
    style B2 fill:#ffe1e1
    style D1 fill:#e1ffe1
    style E4 fill:#fff3e1
    style F3 fill:#e1e1ff
```

---

## Diagram 4: Component Interaction Sequence

```mermaid
sequenceDiagram
    participant Sensor as Health Sensors
    participant WearOS as Wear OS App
    participant TFLite as TFLite Models
    participant Room as Room Database
    participant Cloud as Cloud Backend
    participant SageMaker as AWS SageMaker
    participant Dashboard as Mobile Dashboard
    
    Note over Sensor,WearOS: Every 5 seconds
    Sensor->>WearOS: Raw sensor data<br/>(HR, Accel, Gyro)
    
    WearOS->>WearOS: Preprocess & Buffer<br/>(100 samples)
    
    WearOS->>TFLite: Run Activity Classifier
    TFLite-->>WearOS: Activity State<br/>(e.g., RUNNING)
    
    WearOS->>WearOS: Calculate Personal Baseline<br/>for RUNNING state
    
    WearOS->>TFLite: Run Anomaly Detector<br/>(current + baseline)
    TFLite-->>WearOS: Anomaly Score: 0.85
    
    alt Score > 0.8 (Critical)
        WearOS->>WearOS: Trigger Alert<br/>Notification
        Note over WearOS: Total latency: 137ms
    end
    
    WearOS->>Room: Store data locally
    
    Note over Room,Cloud: Every 30 minutes
    Room->>Cloud: Batch sync<br/>(compressed data)
    Cloud->>Cloud: API Gateway → Lambda
    Cloud->>Cloud: Store in DynamoDB
    
    Note over Cloud,SageMaker: Weekly (Sunday 00:00)
    Cloud->>SageMaker: Trigger training job<br/>(aggregated data)
    SageMaker->>SageMaker: Train LSTM models<br/>(45 min on GPU)
    SageMaker->>SageMaker: Optimize to TFLite<br/>(quantize + prune)
    SageMaker-->>Cloud: Upload to S3 Registry
    
    Cloud->>WearOS: Push model update<br/>(OTA - 0.8 MB)
    WearOS->>TFLite: Load new models
    
    Note over Dashboard: User opens app
    Dashboard->>Cloud: Request historical data
    Cloud-->>Dashboard: Return time-series<br/>+ insights
    Dashboard->>Dashboard: Render charts<br/>& analytics
```

---

## Diagram 5: ML Model Architecture - Activity Classifier

```mermaid
graph TD
    subgraph "Input Layer"
        A[Input Shape: 100, 6<br/>100 timesteps × 6 features<br/>accel_xyz + gyro_xyz]
    end
    
    subgraph "Feature Extraction"
        B[Conv1D Layer<br/>32 filters, kernel=5<br/>Activation: ReLU]
        C[MaxPooling1D<br/>pool_size=2<br/>Output: 50, 32]
    end
    
    subgraph "Sequence Learning"
        D[LSTM Layer 1<br/>64 units<br/>return_sequences=True]
        E[LSTM Layer 2<br/>32 units<br/>return_sequences=False]
    end
    
    subgraph "Regularization"
        F[Dropout Layer<br/>rate=0.3]
    end
    
    subgraph "Classification"
        G[Dense Layer<br/>16 units, ReLU]
        H[Output Layer<br/>6 units, Softmax<br/>Sleep/Rest/Walk/Run/Exercise/Other]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    
    subgraph "Optimization"
        I[Post-training Quantization<br/>FP32 → INT8]
        J[TFLite Conversion]
        K[Final Model: 0.6 MB<br/>Inference: 45ms]
    end
    
    H --> I
    I --> J
    J --> K
    
    style A fill:#e1f5ff
    style D fill:#ffe1e1
    style E fill:#ffe1e1
    style H fill:#90ee90
    style K fill:#ffd700
```

---

## Diagram 6: ML Model Architecture - LSTM Autoencoder

```mermaid
graph TB
    subgraph "Input"
        A[Input Shape: 50, 4<br/>50 timesteps × 4 features<br/>HR, Steps, Activity, Baseline_Dev]
    end
    
    subgraph "Encoder - Compression"
        B1[LSTM 64 units<br/>return_sequences=True]
        B2[LSTM 32 units<br/>return_sequences=True]
        B3[LSTM 16 units<br/>return_sequences=False]
        B4[Latent Representation<br/>16-dimensional vector]
    end
    
    subgraph "Decoder - Reconstruction"
        C1[RepeatVector<br/>Repeat 50 times]
        C2[LSTM 16 units<br/>return_sequences=True]
        C3[LSTM 32 units<br/>return_sequences=True]
        C4[LSTM 64 units<br/>return_sequences=True]
        C5[TimeDistributed Dense<br/>4 units, linear]
    end
    
    subgraph "Output"
        D[Reconstructed Output<br/>50, 4<br/>Same shape as input]
    end
    
    subgraph "Loss Calculation"
        E[Calculate MSE<br/>Original vs Reconstructed]
        F{Reconstruction<br/>Error}
        G[Score < 0.6<br/>Normal]
        H[Score 0.6-0.8<br/>Warning]
        I[Score > 0.8<br/>Critical Alert]
    end
    
    A --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> C5
    C5 --> D
    
    A --> E
    D --> E
    E --> F
    F --> G
    F --> H
    F --> I
    
    style B4 fill:#ffd700
    style G fill:#90ee90
    style H fill:#ffa500
    style I fill:#ff6b6b
```

---

## Diagram 7: Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        A1[Local Machine<br/>Python + TensorFlow]
        A2[Jupyter Notebooks<br/>Model Experimentation]
        A3[Git Repository<br/>Version Control]
    end
    
    subgraph "Cloud Training Infrastructure"
        B1[AWS SageMaker<br/>ml.p3.2xlarge GPU]
        B2[Training Job<br/>LSTM Models]
        B3[Hyperparameter Tuning<br/>Optuna Optimization]
        B4[Model Validation<br/>Test Dataset]
    end
    
    subgraph "Model Registry"
        C1[S3 Bucket<br/>Model Artifacts]
        C2[Model Versioning<br/>Semantic Versioning]
        C3[Metadata Storage<br/>Performance Metrics]
    end
    
    subgraph "CI/CD Pipeline"
        D1[GitHub Actions<br/>Automated Tests]
        D2[Model Conversion<br/>TFLite Pipeline]
        D3[Quality Gates<br/>Accuracy > 90%]
        D4[A/B Testing<br/>10% rollout first]
    end
    
    subgraph "Production Edge Devices"
        E1[Wear OS Watches<br/>Group A - 10%]
        E2[Wear OS Watches<br/>Group B - 90%]
        E3[Performance Monitoring<br/>Latency, Accuracy]
    end
    
    subgraph "Monitoring & Feedback"
        F1[CloudWatch Metrics<br/>Model Performance]
        F2[User Feedback<br/>Alert Accuracy]
        F3[Retraining Trigger<br/>Performance Degradation]
    end
    
    A1 --> A2
    A2 --> A3
    A3 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4
    
    D4 -->|New Model v1.2| E1
    D4 -->|Stable Model v1.1| E2
    
    E1 --> E3
    E2 --> E3
    E3 --> F1
    E3 --> F2
    F1 --> F3
    F2 --> F3
    F3 --> B1
    
    style B1 fill:#e1ffe1
    style C1 fill:#fff3e1
    style D3 fill:#ffa500
    style E1 fill:#87ceeb
    style E2 fill:#87ceeb
```

---

## Diagram 8: Data Privacy & Security Flow

```mermaid
flowchart TD
    A[Health Sensors] --> B{Data Classification}
    
    B -->|PII - Sensitive| C[On-Device Only<br/>No Cloud Sync]
    B -->|Health Metrics| D[Anonymization Layer]
    
    C --> E[Encrypted Storage<br/>Room DB - AES-256]
    
    D --> F[Remove User ID<br/>Add Random Hash]
    F --> G[Data Minimization<br/>Only necessary fields]
    G --> H[TLS 1.3 Encryption<br/>In Transit]
    
    H --> I{Cloud Storage}
    
    I --> J[DynamoDB<br/>Encrypted at Rest]
    I --> K[S3 Backup<br/>Server-side Encryption]
    
    J --> L[Federated Learning<br/>No Raw Data Shared]
    L --> M[Aggregated Insights<br/>Differential Privacy]
    M --> N[Model Training<br/>Privacy-Preserving]
    
    N --> O[TFLite Model<br/>No Personal Data]
    O --> P[OTA Update<br/>Signed & Verified]
    P --> Q[Wear OS Device]
    
    E --> R[User Data Export<br/>GDPR Compliance]
    E --> S[Right to Deletion<br/>GDPR Compliance]
    
    style C fill:#ff6b6b
    style E fill:#90ee90
    style L fill:#87ceeb
    style O fill:#ffd700
```

---

## Usage Instructions

### How to Use These Diagrams:

1. **In Markdown/GitHub**: 
   - Copy the code blocks directly into your `.md` files
   - GitHub will automatically render Mermaid diagrams

2. **In Documentation Tools**:
   - Paste into tools that support Mermaid (GitBook, Notion, etc.)

3. **Convert to Images**:
   - Use Mermaid Live Editor: https://mermaid.live/
   - Copy code → Export as PNG/SVG

4. **In Presentations**:
   - Generate images from Mermaid Live Editor
   - Insert into PowerPoint/Google Slides

5. **In VS Code**:
   - Install "Markdown Preview Mermaid Support" extension
   - Preview diagrams directly in editor

### Customization Tips:

- **Change colors**: Modify `style` statements at the end of diagrams
- **Adjust layout**: Change `graph TB` (top-bottom) to `graph LR` (left-right)
- **Add notes**: Use `Note over Component: Your text here`
- **Styling**: Use `fill:#color` for backgrounds, `stroke:#color` for borders

### Color Scheme Used:

- `#e1f5ff` - Light blue (Sensors/Input)
- `#ffe1e1` - Light red (ML Models/Processing)
- `#e1ffe1` - Light green (Cloud/Training)
- `#fff3e1` - Light orange (Storage/Registry)
- `#e1e1ff` - Light purple (Deployment)
- `#ffd700` - Gold (Important/Optimized)
- `#ff6b6b` - Red (Alerts/Critical)
- `#90ee90` - Green (Success/Normal)
- `#ffa500` - Orange (Warning)
- `#87ceeb` - Sky blue (Edge Computing)
