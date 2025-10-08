"""
Generate synthetic health monitoring data for model training and testing
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

def generate_normal_data(n_samples=10000, user_id='user_001'):
    """
    Generate normal health metrics data
    """
    # Time stamps (5-second intervals over several days)
    start_time = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [start_time + timedelta(seconds=5*i) for i in range(n_samples)]
    
    # Normal heart rate (60-100 BPM) with circadian rhythm
    base_hr = 70
    hr_amplitude = 15
    hr_noise = np.random.normal(0, 3, n_samples)
    circadian = hr_amplitude * np.sin(2 * np.pi * np.arange(n_samples) / (24 * 60 * 12))  # 24-hour cycle
    heart_rate = base_hr + circadian + hr_noise
    heart_rate = np.clip(heart_rate, 50, 100)
    
    # Steps (cumulative throughout day, reset at midnight)
    daily_steps = 8000
    steps_per_interval = daily_steps / (24 * 60 * 12)  # 5-second intervals
    steps = np.cumsum(np.random.poisson(steps_per_interval, n_samples))
    # Reset at midnight
    for i in range(len(steps)):
        if timestamps[i].hour == 0 and timestamps[i].minute == 0:
            steps[i:] -= steps[i]
    
    # Calories (correlated with steps and heart rate)
    calories = (steps * 0.04) + (heart_rate * 0.5) + np.random.normal(0, 10, n_samples)
    calories = np.clip(calories, 0, None)
    
    # Distance (correlated with steps)
    distance = steps * 0.8 + np.random.normal(0, 50, n_samples)
    distance = np.clip(distance, 0, None)
    
    df = pd.DataFrame({
        'userId': user_id,
        'timestamp': [int(t.timestamp() * 1000) for t in timestamps],
        'datetime': timestamps,
        'heartRate': heart_rate,
        'steps': steps.astype(int),
        'calories': calories,
        'distance': distance,
        'label': 0  # 0 = normal
    })
    
    return df


def generate_anomalous_data(n_samples=1000, user_id='user_001'):
    """
    Generate anomalous health metrics data
    """
    # Generate base normal data
    df = generate_normal_data(n_samples, user_id)
    
    # Inject anomalies
    anomaly_indices = np.random.choice(n_samples, size=int(n_samples * 0.1), replace=False)
    
    for idx in anomaly_indices:
        anomaly_type = np.random.choice(['high_hr', 'low_hr', 'sudden_change'])
        
        if anomaly_type == 'high_hr':
            # Abnormally high heart rate (150-180 BPM)
            df.loc[idx:idx+10, 'heartRate'] = np.random.uniform(150, 180, min(11, n_samples - idx))
        
        elif anomaly_type == 'low_hr':
            # Abnormally low heart rate (30-40 BPM)
            df.loc[idx:idx+10, 'heartRate'] = np.random.uniform(30, 40, min(11, n_samples - idx))
        
        elif anomaly_type == 'sudden_change':
            # Sudden spike or drop
            df.loc[idx, 'heartRate'] = np.random.choice([180, 35])
    
    # Mark anomalies
    df.loc[anomaly_indices, 'label'] = 1  # 1 = anomaly
    
    return df


def generate_test_scenarios():
    """
    Generate specific test scenarios
    """
    scenarios = []
    
    # Scenario 1: Exercise (elevated heart rate for extended period)
    exercise_data = generate_normal_data(500, 'user_test_01')
    exercise_data.loc[100:300, 'heartRate'] = np.random.uniform(130, 160, 201)
    exercise_data.loc[100:300, 'label'] = 0  # This is normal during exercise
    scenarios.append(('exercise', exercise_data))
    
    # Scenario 2: Sleep (low heart rate)
    sleep_data = generate_normal_data(500, 'user_test_02')
    sleep_data.loc[100:300, 'heartRate'] = np.random.uniform(55, 65, 201)
    sleep_data.loc[100:300, 'label'] = 0  # This is normal during sleep
    scenarios.append(('sleep', sleep_data))
    
    # Scenario 3: Tachycardia (abnormally high heart rate)
    tachy_data = generate_normal_data(500, 'user_test_03')
    tachy_data.loc[100:300, 'heartRate'] = np.random.uniform(150, 180, 201)
    tachy_data.loc[100:300, 'label'] = 1  # This is abnormal at rest
    scenarios.append(('tachycardia', tachy_data))
    
    # Scenario 4: Bradycardia (abnormally low heart rate)
    brady_data = generate_normal_data(500, 'user_test_04')
    brady_data.loc[100:300, 'heartRate'] = np.random.uniform(30, 45, 201)
    brady_data.loc[100:300, 'label'] = 1  # This is abnormal
    scenarios.append(('bradycardia', brady_data))
    
    return scenarios


def main():
    """
    Main function to generate all datasets
    """
    # Create directories
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    os.makedirs('data/synthetic', exist_ok=True)
    
    print("Generating synthetic health monitoring data...")
    
    # Generate training data
    print("1. Generating normal training data...")
    normal_data = generate_normal_data(n_samples=20000)
    normal_data.to_csv('data/synthetic/normal_data.csv', index=False)
    print(f"   Saved {len(normal_data)} normal samples")
    
    # Generate anomalous data
    print("2. Generating anomalous data...")
    anomalous_data = generate_anomalous_data(n_samples=5000)
    anomalous_data.to_csv('data/synthetic/anomalous_data.csv', index=False)
    print(f"   Saved {len(anomalous_data)} samples with anomalies")
    
    # Combine for training
    print("3. Creating combined dataset...")
    combined_data = pd.concat([normal_data, anomalous_data], ignore_index=True)
    combined_data = combined_data.sample(frac=1).reset_index(drop=True)  # Shuffle
    combined_data.to_csv('data/processed/health_metrics.csv', index=False)
    print(f"   Saved {len(combined_data)} combined samples")
    
    # Generate test scenarios
    print("4. Generating test scenarios...")
    scenarios = generate_test_scenarios()
    for scenario_name, scenario_data in scenarios:
        scenario_data.to_csv(f'data/synthetic/{scenario_name}_scenario.csv', index=False)
        print(f"   Saved {scenario_name} scenario ({len(scenario_data)} samples)")
    
    # Generate statistics
    print("\n📊 Dataset Statistics:")
    print(f"   Total samples: {len(combined_data)}")
    print(f"   Normal samples: {len(combined_data[combined_data['label'] == 0])}")
    print(f"   Anomalous samples: {len(combined_data[combined_data['label'] == 1])}")
    print(f"   Anomaly ratio: {len(combined_data[combined_data['label'] == 1]) / len(combined_data) * 100:.2f}%")
    print(f"\n   Heart Rate - Mean: {combined_data['heartRate'].mean():.2f}, Std: {combined_data['heartRate'].std():.2f}")
    print(f"   Heart Rate - Min: {combined_data['heartRate'].min():.2f}, Max: {combined_data['heartRate'].max():.2f}")
    
    print("\n✅ Data generation complete!")


if __name__ == "__main__":
    main()
