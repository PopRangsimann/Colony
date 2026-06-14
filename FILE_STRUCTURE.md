# Colony Framework: File Structure and Explanation

This document provides a comprehensive overview of the files in the Colony project. For each file, it details the **Name**, **Purpose**, and **Where it is used**.

## Root Directory

### 1. `config.py`
* **Purpose**: Central configuration file containing all tunable values, thresholds, weights, and parameters used throughout the project (e.g., node counts, cryptography configurations, equation weights).
* **Where it is used**: Imported by almost all modules across the framework to ensure consistent parameters without hardcoding values inline.

### 2. `run_all_phases.py`
* **Purpose**: A full pipeline demonstration script that sequentially executes Phase 1 through Phase 6 to demonstrate the complete stability-aware load-balancing framework.
* **Where it is used**: Executed by the user via the command line to run a quick, end-to-end simulation of the Colony system.

### 3. `README.md`
* **Purpose**: Provides a high-level overview of the project and basic instructions for running the evaluation.
* **Where it is used**: Read by developers and users as the entry point to understand the project repository.

---

## `phase1_system_init/`

### 4. `attribute_authority.py`
* **Purpose**: Manages the initialization of the CP-ABE (Ciphertext-Policy Attribute-Based Encryption) system, defining the attribute universe and generating secret keys for users.
* **Where it is used**: Used during the system startup (Phase 1) and by the result retrieval phase (Phase 6) to authorize access to outputs.

### 5. `comm_init.py`
* **Purpose**: Handles the initial communication setup and secure channel establishment using Kyber (Post-Quantum Key Encapsulation Mechanism).
* **Where it is used**: Used during node startup to establish secure session keys between IIoT devices and fog nodes/gateways.

### 6. `crp_database.py`
* **Purpose**: Maintains the Challenge-Response Pair (CRP) database necessary for PUF (Physical Unclonable Function) authentication.
* **Where it is used**: Used by the edge gateway or fog nodes to authenticate incoming IIoT devices securely before accepting data.

### 7. `fog_node.py`
* **Purpose**: Defines the `FogNode` class, representing the computational nodes in the fog layer. Handles node properties like CPU, memory, latency, and status.
* **Where it is used**: Instantiated during Phase 1 and used throughout all subsequent phases to simulate the fog network's state and processing behavior.

### 8. `demo.py`
* **Purpose**: Demonstrates the execution of Phase 1 in isolation.
* **Where it is used**: Called by `run_all_phases.py` and can be run individually for testing Phase 1 setup.

---

## `phase2_iiot_protection/`

### 9. `iiot_device.py`
* **Purpose**: Defines the `IIoTDevice` class, representing end devices that generate sensed data, maintain internal states, and initiate transmissions.
* **Where it is used**: Used heavily in Phase 2 to simulate the data generation and device-side logic before sending to the fog layer.

### 10. `key_derivation.py`
* **Purpose**: Derives symmetric session keys from the shared secrets established via Kyber.
* **Where it is used**: Used by both IIoT devices and edge gateways to synchronize their encryption keys for high-speed symmetric encryption.

### 11. `packet_protection.py`
* **Purpose**: Applies ChaCha20-Poly1305 encryption and Message Authentication Codes (MAC) to IIoT data packets to ensure integrity and prevent tampering/replay attacks.
* **Where it is used**: Used on the IIoT device side directly before data packets are transmitted over the network.

### 12. `demo.py`
* **Purpose**: Demonstrates the execution of Phase 2 (IIoT data protection).
* **Where it is used**: Called by `run_all_phases.py` and can be run individually for testing Phase 2.

---

## `phase3_workload_profiling/`

### 13. `gateway.py`
* **Purpose**: Defines the edge gateway, acting as an intermediate layer that receives, validates, and batches traffic from IIoT devices.
* **Where it is used**: Bridging the IIoT device layer and the Fog computing layer.

### 14. `packet_validation.py`
* **Purpose**: Validates the cryptographic integrity, authenticity, and freshness of packets received from IIoT devices.
* **Where it is used**: Invoked by the edge gateway upon receiving any packet to discard tampered or replayed data.

### 15. `batch_formation.py`
* **Purpose**: Groups validated incoming packets into micro-batches to improve processing efficiency and throughput.
* **Where it is used**: Used by the gateway immediately after packet validation.

### 16. `workload_profiler.py`
* **Purpose**: Computes metrics like workload intensity (ω), urgency/deadline (δ), and recovery priority (ρ) for each micro-batch.
* **Where it is used**: Used by the gateway or master node before workloads are passed to the scheduler in Phase 4.

### 17. `demo.py`
* **Purpose**: Demonstrates Phase 3 (workload validation and profiling).
* **Where it is used**: Called by `run_all_phases.py`.

---

## `phase4_load_balancing/`

### 18. `coordinator_election.py`
* **Purpose**: Evaluates fog nodes and elects the Master Fog Node (MFN) and Secondary Master Fog Node (SMFN) based on readiness and capability scores.
* **Where it is used**: Used continuously or periodically to ensure the fog cluster has active leadership.

### 19. `fri.py`
* **Purpose**: Calculates the Failure Resilience Index (FRI) for fog nodes, measuring their reliability.
* **Where it is used**: Used during coordinator election and task scheduling to avoid assigning critical tasks to unreliable nodes.

### 20. `scheduler.py`
* **Purpose**: Schedules and distributes micro-batches across fog nodes based on queue depth, capabilities, and FRI.
* **Where it is used**: Central logic executed by the MFN to balance the load across the fog network.

### 21. `state_replication.py`
* **Purpose**: Replicates the MFN's state (schedules, metadata) to the SMFN and cache nodes to ensure state consistency.
* **Where it is used**: Used by the MFN after every scheduling cycle to prepare for potential failure recovery.

### 22. `demo.py`
* **Purpose**: Demonstrates Phase 4 (load balancing and coordinator election).
* **Where it is used**: Called by `run_all_phases.py`.

---

## `phase5_resource_assistance/`

### 23. `assistance_request.py`
* **Purpose**: Manages requests from fog nodes that are overloaded and at risk of missing deadlines.
* **Where it is used**: Triggered by standard fog nodes when their queue depth or latency exceeds safe thresholds.

### 24. `helper_selection.py`
* **Purpose**: Identifies and selects appropriate helper nodes that have spare capacity (Assistance Budget) to offload tasks.
* **Where it is used**: Invoked by the MFN or the overloaded node to find a suitable peer for offloading.

### 25. `collaborative.py`
* **Purpose**: Manages the actual process of partitioning the workload and migrating it from the overloaded node to the helper node.
* **Where it is used**: Executed during collaborative workload processing to ensure deadlines are met without data loss.

### 26. `demo.py`
* **Purpose**: Demonstrates Phase 5 (resource assistance and offloading).
* **Where it is used**: Called by `run_all_phases.py`.

---

## `phase6_recovery_and_results/`

### 27. `failure_detection.py`
* **Purpose**: Monitors heartbeat signals to detect the failure of fog nodes, specifically the MFN or SMFN.
* **Where it is used**: Run constantly by the SMFN (to monitor the MFN) and by other fog nodes (to monitor the SMFN).

### 28. `leadership_recovery.py`
* **Purpose**: Orchestrates Level 1 (SMFN takes over) and Level 2 (cluster re-election) recovery processes.
* **Where it is used**: Triggered immediately upon detection of a failure by `failure_detection.py`.

### 29. `result_manager.py`
* **Purpose**: Secures final computation results by encrypting them with AES-GCM and encrypting the AES key using CP-ABE access policies.
* **Where it is used**: Used by fog nodes right after they finish processing a micro-batch.

### 30. `result_retrieval.py`
* **Purpose**: Provides mechanisms for authorized clients to request, decrypt, and verify the final processed results using their CP-ABE attributes.
* **Where it is used**: Used by end-users, administrators, or downstream systems consuming the processed data.

### 31. `demo.py`
* **Purpose**: Demonstrates Phase 6 (leadership recovery and secure result retrieval).
* **Where it is used**: Called by `run_all_phases.py`.

---

## `crypto_primitives/`
*(These files provide underlying security mechanisms and are used extensively across all phases)*

### 32. `aes_gcm.py`, `chacha20.py`
* **Purpose**: Implementations of symmetric encryption algorithms for high-speed data protection.
* **Where it is used**: `chacha20.py` for device-to-gateway (Phase 2), `aes_gcm.py` for final results (Phase 6).

### 33. `cp_abe.py`
* **Purpose**: Ciphertext-Policy Attribute-Based Encryption for fine-grained access control.
* **Where it is used**: Protecting final processing results so only authorized users can read them (Phases 1 and 6).

### 34. `dilithium.py`, `kyber.py`
* **Purpose**: Post-Quantum Cryptography implementations (Dilithium for signatures, Kyber for Key Encapsulation).
* **Where it is used**: Initial secure channel establishment and digital signatures (Phase 1 and 2).

### 35. `puf.py`
* **Purpose**: Simulates Physical Unclonable Functions for hardware-based identity.
* **Where it is used**: IIoT device authentication (Phase 1).

---

## `evaluation/`
*(These files are responsible for running large-scale simulations to generate paper results, separate from the core framework)*

### 36. `simulator.py`, `environment.py`
* **Purpose**: Core engine for running simulated topologies, integrating all phases into a time-stepped environment.
* **Where it is used**: Driven by `run_all.py` to test the framework under load.

### 37. `metrics.py`, `plotting.py`
* **Purpose**: Calculates performance metrics (e.g., latency, throughput, failure rates) and plots them into graphs.
* **Where it is used**: At the end of simulation runs to produce visualizations.

### 38. `sim_config.py`, `run_all.py`
* **Purpose**: Configures baseline scenarios against other comparison schemes and acts as the entry script for all evaluations.
* **Where it is used**: Run by researchers to generate all comparative charts and data.
