#!/usr/bin/env python3
"""
ML Pipeline Test Runner

Orchestrates all test suites and generates comprehensive test reports.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any


class TestRunner:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.test_dir = self.base_dir / "src" / "tests"
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_suites": {},
            "summary": {
                "total_suites": 0,
                "passed_suites": 0,
                "failed_suites": 0,
                "total_duration_seconds": 0,
            }
        }
    
    def run_command(self, cmd: List[str], timeout: int = 300) -> Dict[str, Any]:
        """Run a command and capture output"""
        print(f"  Running: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.base_dir
            )
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "duration_seconds": duration,
            }
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "success": False,
                "error": "Timeout expired",
                "duration_seconds": duration,
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": duration,
            }
    
    def run_tflite_tests(self, benchmark: bool = False) -> Dict[str, Any]:
        """Run TFLite model tests"""
        print("\n[1/5] Running TFLite Model Tests...")
        
        cmd = [
            sys.executable,
            str(self.test_dir / "tflite_smoketest.py"),
            "--activity", "models/tflite/activity_classifier.tflite",
            "--anomaly", "models/tflite/anomaly_lstm.tflite",
        ]
        
        if benchmark:
            cmd.extend(["--benchmark", "--benchmark-iterations", "50"])
        
        result = self.run_command(cmd)
        
        # Try to parse JSON output
        if result["success"] and result["stdout"]:
            try:
                # Extract JSON from output
                lines = result["stdout"].split('\n')
                json_start = None
                for i, line in enumerate(lines):
                    if line.strip().startswith('{'):
                        json_start = i
                        break
                
                if json_start is not None:
                    json_text = '\n'.join(lines[json_start:])
                    # Find the end of JSON
                    brace_count = 0
                    json_end = 0
                    for i, char in enumerate(json_text):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    
                    if json_end > 0:
                        result["parsed_output"] = json.loads(json_text[:json_end])
            except Exception as e:
                result["parse_error"] = str(e)
        
        return result
    
    def run_sklearn_tests(self, benchmark: bool = False) -> Dict[str, Any]:
        """Run sklearn model tests"""
        print("\n[2/5] Running Scikit-learn Model Tests...")
        
        cmd = [
            sys.executable,
            str(self.test_dir / "test_sklearn_models.py"),
            "--model", "models/saved_models/isolation_forest.pkl",
            "--scaler", "models/saved_models/scaler.pkl",
        ]
        
        if benchmark:
            cmd.extend(["--benchmark", "--benchmark-iterations", "50"])
        
        return self.run_command(cmd)
    
    def run_lambda_tests(self) -> Dict[str, Any]:
        """Run Lambda export tests"""
        print("\n[3/5] Running Lambda Export Tests...")
        
        cmd = [
            sys.executable,
            str(self.test_dir / "test_lambda_export.py"),
            "--export-dir", "models/lambda_export",
            "--batch-size", "100",
            "--simulate-lambda",
        ]
        
        return self.run_command(cmd)
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        print("\n[4/5] Running Integration Tests...")
        
        cmd = [
            sys.executable,
            str(self.test_dir / "test_integration.py"),
            "--tflite-dir", "models/tflite",
            "--lambda-export", "models/lambda_export",
        ]
        
        return self.run_command(cmd)
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check if all required dependencies are installed"""
        print("\n[5/5] Checking Dependencies...")
        
        required_packages = [
            "numpy",
            "tensorflow",
            "joblib",
            "scikit-learn",
        ]
        
        missing = []
        installed = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                installed.append(package)
            except ImportError:
                missing.append(package)
        
        return {
            "success": len(missing) == 0,
            "installed": installed,
            "missing": missing,
            "duration_seconds": 0.1,
        }
    
    def run_all_tests(self, benchmark: bool = False, skip_integration: bool = False) -> None:
        """Run all test suites"""
        print("="*80)
        print("ML PIPELINE - COMPREHENSIVE TEST SUITE")
        print("="*80)
        
        start_time = time.time()
        
        # Check dependencies
        dep_result = self.check_dependencies()
        self.results["test_suites"]["dependencies"] = dep_result
        
        if not dep_result["success"]:
            print(f"\n⚠️  Missing dependencies: {dep_result['missing']}")
            print("Install with: pip install " + " ".join(dep_result['missing']))
            self.results["summary"]["failed_suites"] += 1
        else:
            print(f"✅ All dependencies installed")
        
        # Run test suites
        test_suites = [
            ("tflite_models", lambda: self.run_tflite_tests(benchmark)),
            ("sklearn_models", lambda: self.run_sklearn_tests(benchmark)),
            ("lambda_export", self.run_lambda_tests),
        ]
        
        if not skip_integration:
            test_suites.append(("integration", self.run_integration_tests))
        
        for suite_name, test_func in test_suites:
            self.results["summary"]["total_suites"] += 1
            result = test_func()
            self.results["test_suites"][suite_name] = result
            
            if result["success"]:
                self.results["summary"]["passed_suites"] += 1
                print(f"  ✅ {suite_name}: PASSED ({result['duration_seconds']:.2f}s)")
            else:
                self.results["summary"]["failed_suites"] += 1
                print(f"  ✗ {suite_name}: FAILED ({result['duration_seconds']:.2f}s)")
                if "error" in result:
                    print(f"     Error: {result['error']}")
        
        self.results["summary"]["total_duration_seconds"] = time.time() - start_time
    
    def generate_report(self, output_file: str = None) -> None:
        """Generate test report"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        summary = self.results["summary"]
        print(f"Total Suites:    {summary['total_suites']}")
        print(f"Passed:          {summary['passed_suites']} ✅")
        print(f"Failed:          {summary['failed_suites']} ✗")
        print(f"Total Duration:  {summary['total_duration_seconds']:.2f}s")
        
        # Detailed results
        print("\n" + "="*80)
        print("DETAILED RESULTS")
        print("="*80)
        
        for suite_name, result in self.results["test_suites"].items():
            status = "✅ PASSED" if result["success"] else "✗ FAILED"
            print(f"\n{suite_name}: {status}")
            print(f"  Duration: {result['duration_seconds']:.2f}s")
            
            if not result["success"]:
                if "error" in result:
                    print(f"  Error: {result['error']}")
                if "stderr" in result and result["stderr"]:
                    print(f"  stderr:\n{result['stderr'][:500]}")
        
        # Save to file
        if output_file:
            output_path = self.base_dir / output_file
            with open(output_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n📄 Full report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run ML Pipeline test suite")
    parser.add_argument("--base-dir", default=".", help="Base directory of ML pipeline")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--skip-integration", action="store_true", help="Skip integration tests")
    parser.add_argument("--output", default="test_results.json", help="Output file for results")
    args = parser.parse_args()
    
    # Change to base directory
    base_dir = Path(args.base_dir).resolve()
    
    if not (base_dir / "src" / "tests").exists():
        print(f"❌ Error: Test directory not found at {base_dir / 'src' / 'tests'}")
        print(f"   Make sure you're running from the MLPipeline directory")
        sys.exit(1)
    
    # Run tests
    runner = TestRunner(str(base_dir))
    runner.run_all_tests(benchmark=args.benchmark, skip_integration=args.skip_integration)
    runner.generate_report(args.output)
    
    # Exit with appropriate code
    if runner.results["summary"]["failed_suites"] > 0:
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
