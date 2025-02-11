# Zaki Araujo

--------------------------------------

## **Part 1:  AGILE**

**Theme:** Get GiggleGit demo into a stable enough alpha to start onboarding some adventurous clients

**Epic:** Onboarding experience 

### User Story 1: 
As a vanilla git power-user that has never seen GiggleGit before, I want to ... **Quickly set up GiggleGit and set it up to work with my existing workflow without pain hours of trouble shooting.**

### User Story 2: 
As a team lead onboarding an experienced GiggleGit user, I want to … **Ensure that my team can collaborate effectively with minimal learning curve.**

### User Story 3: 
As a developer using GiggleGit, I want to customize my merge process with configurable strategies, quickly revert bad merges, and access a detailed merge history so that I can efficiently resolve conflicts.

### Task: Implement customizable merge functionality.

- **Ticket 1:** Create a plugin or visual tool that integrates with GiggleGit to visualize branch activities in real time. The extension/plugin should display a graphical representation of branch hierarchies, clearly indicating which branches are being merged, overwritten, or are pending changes. 

- **Ticket 2:** Create a mechanism for quickly reverting merges when mistakes occur, and implement a searchable merge history log that records key details such as timestamps, chosen strategies, and conflict resolutions for effective auditing and troubleshooting.

*********************

## **Part 2: Formal Requirements**

CodeChuckle is introducing a new diff tool: SnickerSync—why merge in silence when you can sync with a snicker? The PMs have a solid understanding of what it means to "sync with a snicker" and now they want to run some user studies. Your team has already created a vanilla interface capable of syncing with the base GiggleGit packages.

**Goal:** Enable users to experience a seamless diff tool experience by integrating the sync with a snicker feature.

**Non-Goal:** SnickerSync is not intended to replace the core functionality of existing diff tools but to complement them.

### Non-functional Requirement 1: 
#### 1. Access Control
- **Non-Functional Requirement:** Ensure that only authorized users have access to specific features and data within SnickerSync.
  - **Functional Requirement 1:** Implement restricted access to sensitive features and data.
  - **Functional Requirement 2:** Provide an authentication mechanism to verify user identity before granting access.

### Non-functional Requirement 2:
#### 2. Maintainability of Snickering Concepts
- **Non-Functional Requirement:** PMs should be able to easily maintain and update the different "snickering" concepts without requiring extensive technical knowledge.
  - **Functional Requirement 1:** Develop an admin panel where PMs can manage and update snickering concepts.
  - **Functional Requirement 2:** Provide documentation and training materials to assist PMs in maintaining snickering concepts effectively.