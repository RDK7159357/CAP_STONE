# Real-Time Health Monitoring System on Wear OS: A Capstone Project Report

---

## Document Formatting Specifications

**Font Family:** Times New Roman (12 pt body text)  
**Line Spacing:** Double-spaced (2.0)  
**Margins:** 1 inch (top, bottom, left, right)  
**Page Size:** Letter (8.5" × 11")  
**Alignment:** Justified  
**Heading Hierarchy:**
- Title (16 pt, bold, centered)
- Chapter Headings (14 pt, bold)
- Section Headings (12 pt, bold)
- Subsection Headings (12 pt, bold, italicized)

---

## Table of Contents

### Front Matter
- **Index** (This page)

### Main Chapters

1. [**Abstract and Executive Summary**](ACADEMIC_REPORT_00_ABSTRACT.md)
   - Overview of objectives, implementation, and findings
   - Executive summary with current status and future roadmap

2. [**Chapter 1: Introduction**](ACADEMIC_REPORT_01_INTRODUCTION.md)
   - Problem statement and project motivation
   - Objectives and scope
   - Current system snapshot

3. [**Chapter 2: Literature Review**](ACADEMIC_REPORT_02_LITERATURE_REVIEW.md)
   - Related work in wearable health monitoring
   - Machine learning on edge devices
   - Positioning within academic landscape
   - Current implementation stance

4. [**Chapter 3: System Architecture**](ACADEMIC_REPORT_03_SYSTEM_ARCHITECTURE.md)
   - High-level system design (edge-only implementation)
   - Component interactions and data flow
   - Architecture diagrams (7 visual references)
   - Planned future hybrid architecture
   - Processing pipeline and constraints

5. [**Chapter 4: Machine Learning Methodology**](ACADEMIC_REPORT_04_ML_METHODOLOGY.md)
   - ML scope and objectives
   - Activity classification model (10×4 inputs)
   - Anomaly detection using LSTM autoencoder
   - Data preprocessing and training approach
   - Current limitations and future work

6. [**Chapter 5: Implementation and Testing**](ACADEMIC_REPORT_05_IMPLEMENTATION_TESTING.md)
   - Wear OS application architecture (Kotlin/Compose)
   - Component implementation details
   - Testing performed (model sanity checks, functional smoke tests)
   - Performance and power status
   - Known gaps and testing roadmap

7. [**Chapter 6: Discussion and Future Work**](ACADEMIC_REPORT_06_DISCUSSION_FUTURE_WORK.md)
   - Analysis of current implementation
   - Discussion of design decisions and trade-offs
   - Future work priorities and timeline
   - Roadmap for cloud integration, OTA, personalization

### Back Matter

8. [**References and Bibliography**](ACADEMIC_REPORT_07_REFERENCES.md)
   - Academic and technical references
   - Framework and tool documentation
   - Design and architecture guidelines
   - Related benchmarks and resources

---

## Quick Navigation

### By Topic

**Understanding the Current System:**
- Start with [Abstract](ACADEMIC_REPORT_00_ABSTRACT.md) for a quick overview
- Read [Chapter 1](ACADEMIC_REPORT_01_INTRODUCTION.md) for context and objectives
- Review [Chapter 3](ACADEMIC_REPORT_03_SYSTEM_ARCHITECTURE.md) for architecture and diagrams

**Machine Learning Details:**
- [Chapter 4](ACADEMIC_REPORT_04_ML_METHODOLOGY.md) – ML models and methodology
- [Chapter 5](ACADEMIC_REPORT_05_IMPLEMENTATION_TESTING.md) – Implementation and testing

**Implementation and Testing:**
- [Chapter 5](ACADEMIC_REPORT_05_IMPLEMENTATION_TESTING.md) – Full implementation details

**Future Directions:**
- [Chapter 6](ACADEMIC_REPORT_06_DISCUSSION_FUTURE_WORK.md) – Roadmap and next steps

**Research Context:**
- [Chapter 2](ACADEMIC_REPORT_02_LITERATURE_REVIEW.md) – Literature review and positioning

---

## Document Statistics

- **Total Chapters:** 8 (including Abstract and References)
- **Architecture Diagrams:** 7 visual references
- **References:** 31 academic, technical, and framework sources
- **Scope:** Edge-first health monitoring on Wear OS
- **Current Focus:** Bundled TFLite models, on-device inference, rule-based fallback
- **Future Vision:** Cloud integration, OTA updates, personalization, extended sensing

---

## Key Features

✓ Complete academic structure (Abstract, Chapters, References)
✓ Aligned to current edge-only implementation
✓ Clear distinction between implemented and planned features
✓ Architecture diagrams and visual references
✓ Comprehensive references for further reading
✓ Future work roadmap with priorities

---

**Last Updated:** January 4, 2026  
**Status:** Complete and ready for submission/publication
