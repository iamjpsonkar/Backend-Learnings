# System Design Learning Notes

Practical notes for learning system design from requirements through architecture,
data, scalability, security, operations, and interview case studies.

## Start here

- Follow the [14-lecture course outline](topics.md) for a structured learning path.
- Use the [interview design template](docs/system-design-interview-template.md) to
  work through a new problem consistently.
- Practice with the [catalog of 60 system design examples](system-design-examples/README.md),
  organized by domain and difficulty.
- Jump to the practical case studies: [Google Maps](#google-map-system-design),
  [e-commerce](#e-commerce-platform-system-design), and
  [video streaming](#video-streaming-platform).
- View the architecture diagrams in [`flowdiagrams/`](flowdiagrams/).
- `README.pdf` is a legacy snapshot from December 2023 and may not include the
  latest notes in this document.

## Learning path

| Stage | Focus | Outcome |
| --- | --- | --- |
| 1. Foundations | Requirements, constraints, and trade-offs | Define what success means |
| 2. Building blocks | APIs, databases, caches, queues, and proxies | Select components for a reason |
| 3. Distributed systems | Partitioning, replication, consistency, and failure | Explain behavior under load and failure |
| 4. Operations | Security, observability, deployment, and recovery | Make the design operable |
| 5. Practice | Estimation and case studies | Communicate a defensible end-to-end design |

## A repeatable design workflow

1. Clarify users, scope, core use cases, and explicit exclusions.
2. Make non-functional requirements measurable: traffic, latency, availability,
   consistency, durability, retention, privacy, and cost.
3. Estimate peak requests, storage growth, bandwidth, and concurrency.
4. Define APIs, events, and the data model before drawing infrastructure.
5. Sketch the request and data flows, including trust boundaries.
6. Find bottlenecks and failure modes; then add scaling and resilience mechanisms.
7. Close with trade-offs, observability, rollout, and future evolution.

Useful back-of-the-envelope formulas:

```text
average requests/second = requests/day / 86,400
peak requests/second    = average requests/second * peak factor
storage                 = writes/second * bytes/write * retention seconds * replicas
bandwidth                = requests/second * average payload bytes
concurrency              = requests/second * average request duration in seconds
```

## Overview of System Design

### What is System Design?

**System design** is the process of defining a system's architecture, components,
interfaces, data, and operational characteristics so that it satisfies explicit
functional and non-functional requirements. Good design is not a list of
technologies; it is a set of justified trade-offs under known constraints.

### **Key Aspects of System Design**
1. **Architecture**: The overall structure and organization of the system.
2. **Components**: The building blocks or modules that make up the system.
3. **Interfaces**: How different components interact with each other.
4. **Data Design**: Defining how data will be stored, accessed, and managed.

### **Importance of System Design**

- **Efficiency**: Well-designed systems are efficient, ensuring optimal use of resources.
    - A well-designed system optimizes resource utilization, ensuring efficient operation.
    - It minimizes bottlenecks, and unnecessary operations, and maximizes performance.
- **Scalability**: A good design allows the system to grow and handle increased loads.
    - Scalability refers to the system's ability to handle increased loads and growth.
    - A good system design accommodates scalability, allowing the system to expand as needed.
- **Reliability**: System design aims for a high level of reliability, reducing the chances of system failures.
    - Reliability is about minimizing the chances of system failures.
    - A reliable system is robust, resilient, and capable of recovering gracefully from errors.

### **Principles of System Design**

- **Modularity**:
    - **Definition**:  Breaking down the system into manageable and independent modules or components.
    - **Advantages**: Hiding complex details while exposing necessary functionalities to simplify the system's representation.
- **Abstraction**:
    - **Definition**: Hiding complex details while exposing necessary functionalities.
    - **Advantages**: Enhances clarity, reduces complexity, and allows for a higher-level view.
- **Simplicity**: 
    - **Definition**: Striving for simplicity in design without compromising functionality.
    - **Advantages**: Simplicity aids in understanding, and maintenance, and reduces the chances of errors.

#### **SOLID Principle**
*The SOLID principles are a set of five design principles for writing maintainable and scalable software. These principles were introduced by Robert C. Martin and are widely used in object-oriented programming.*

The SOLID acronym represents the following principles:
- **Single Responsibility Principle (SRP)**:
    - **Principle**: A class should have only one reason to change, meaning it should have only one responsibility.
   - **Explanation**: This principle encourages the design of classes that have a clear and focused purpose. Each class should encapsulate only one aspect of the overall functionality, making the code more modular and easier to maintain.

- **Open/Closed Principle (OCP)**:
   - **Principle**: Software entities (classes, modules, functions, etc.) should be open for extension but closed for modification.
   - **Explanation**: This principle promotes the idea that you should be able to add new functionality to a system without altering the existing code. This is often achieved through the use of interfaces and abstract classes, allowing for extension through new implementations.

- **Liskov Substitution Principle (LSP)**:
   - **Principle**: Objects of a superclass should be replaceable with objects of a subclass without affecting the correctness of the program.
   - **Explanation**: This principle ensures that subtypes can be used interchangeably with their base types without causing errors. It emphasizes the importance of maintaining the expected behavior when substituting one class for another.

- **Interface Segregation Principle (ISP)**:
   - **Principle**: A class should not be forced to implement interfaces it does not use.
   - **Explanation**: This principle advocates for the creation of small, specific interfaces rather than large, general-purpose ones. Clients should not be forced to depend on interfaces they do not use, reducing the impact of changes to the system.

- **Dependency Inversion Principle (DIP):**
   - **Principle**: High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details; details should depend on abstractions.
   - **Explanation**: This principle encourages the use of abstractions (interfaces or abstract classes) to decouple high-level modules from low-level implementations. It promotes flexibility and ease of maintenance by minimizing the impact of changes in the implementation details.

#### **Separation of Concerns (SoC)**
*The principle of Separation of Concerns (SoC) is a fundamental concept in software design that promotes dividing a computer program into distinct sections, each addressing a separate concern. The goal is to create a modular and maintainable system by isolating different aspects of the software, making it easier to understand, develop, and maintain.*

The key concerns often separated in software design include

- **Presentation Concern**:
    - **Responsibility**: Handling the user interface and user interactions.
    - **Example**: HTML, CSS, front-end JavaScript code.
- **Business Logic Concern**:
    - **Responsibility**: Implementing the core functionality or business rules of the application.
    - **Example**: Classes and methods responsible for processing data, enforcing rules, and making decisions.
- **Data Access Concern**:
    - **Responsibility**: Managing the interaction with the data storage, such as databases or external APIs.
    - **Example**: Database queries, data retrieval, and storage operations.
- **Infrastructure Concern**:
    - **Responsibility**: Dealing with system-level concerns like logging, configuration, and external services.
    - **Examples**: Logging mechanisms, configuration management, and third-party integrations.
    
*By separating these concerns, the codebase becomes more modular, and changes in one area are less likely to affect others. This separation enhances the maintainability, reusability, and testability of the software. Developers can work on specific concerns without needing to understand the entire system, leading to more efficient collaboration.*

**Key benefits of Separation of Concerns**:

- **Maintainability**: Changes to one concern do not affect others, making it easier to modify and extend the system.

- **Reusability**: Components that handle specific concerns can be reused in different parts of the application or other projects.

- **Testability**: Isolated concerns are easier to test independently, facilitating the development of unit tests and ensuring the correctness of individual components.

- **Understandability**: Code becomes more readable and comprehensible as each module or class has a clear and distinct purpose.

*Practical techniques for achieving Separation of Concerns include using design patterns (such as MVC - Model-View-Controller), modular programming, and employing abstraction mechanisms like interfaces or abstract classes.*

### **Design Pattern**
*Design patterns are general, reusable solutions to common problems encountered in software design. They represent best practices evolved by experienced software developers. Using design patterns can speed up the development process, improve code organization, and make software systems more scalable and maintainable.*

Here are some commonly used design patterns:

#### **Creational Patterns**:
- **Singleton Pattern**: *Ensures that a class has only one instance and provides a global point of access to it.*
- **Factory Method Pattern**: *Defines an interface for creating an object but leaves the choice of its type to the subclasses, creating an instance of the appropriate subclass.*
- **Abstract Factory Pattern**: *Provides an interface for creating families of related or dependent objects without specifying their concrete classes.*
- **Builder Pattern**: *Separates the construction of a complex object from its representation, allowing the same construction process to create different representations.*
- **Prototype Pattern**: *Creates new objects by copying an existing object, known as the prototype.*

#### **Structural Patterns**:
- **Adapter Pattern**: *Allows the interface of an existing class to be used as another interface.*
- **Bridge Pattern**: *Separates abstraction from implementation so that the two can vary independently.*
- **Composite Pattern**: *Composes objects into tree structures to represent part-whole hierarchies.*
- **Decorator Pattern**: *Attaches additional responsibilities to an object dynamically. Decorators provide a flexible alternative to subclassing for extending functionality.*
- **Facade Pattern**: *Provides a simplified interface to a set of interfaces in a subsystem, making it easier to use.*
- **Flyweight Pattern**: *Minimizes memory usage or computational expenses by sharing as much as possible with related objects.*

#### **Behavioral Patterns**:
- **Observer Pattern**: *Defines a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.*
- **Strategy Pattern**: *Defines a family of algorithms, encapsulates each algorithm, and makes them interchangeable. Strategy lets the algorithm vary independently from clients that use it.*
- **Command Pattern**: *Encapsulates a request as an object, thereby allowing for parameterization of clients with different requests, queuing of requests, and logging of the requests.*
- **Chain of Responsibility Pattern**: *Passes the request along a chain of handlers. Upon receiving a request, each handler decides either to process the request or to pass it to the next handler in the chain.*
- **State Pattern**: *Allows an object to alter its behavior when its internal state changes. The object will appear to change its class.*
- **Visitor Pattern**: *Represents an operation to be performed on the elements of an object structure. Allows the definition of a new operation without changing the classes of the elements on which it operates.*

*These design patterns provide solutions to common design problems and can be adapted to various scenarios in software development. It's important to choose the appropriate pattern based on the specific requirements and constraints of the project.*

### **Different Approaches to System Design**

#### **Top-Down Approach**: 
*Starting with the larger system and breaking it down into smaller components.*

**Overview**:

*The **top-down approach** is a systematic way of designing a system by starting with a high-level view and gradually decomposing it into more detailed components. It's a hierarchical process where the system is broken down into sub-systems or modules, and each module is further refined until the entire system is represented.*

**Steps**:
1. **Start with a General View**: Begin by understanding the system as a whole.
2. **Decomposition**: Break down the system into smaller, more manageable parts.
3. **Refinement**: Continue breaking down each part until detailed components are identified.
4. **Integration**: Combine the detailed components to form the complete system.

**Advantages**:
- **Clarity**: Offers a clear and structured way to understand the system.
- **Progressive Detailing**: Allows for a gradual and detailed development of the system.

**Challenges**:
- **Dependency on Initial Understanding**: The effectiveness depends on the accuracy of the initial high-level view.

#### **Bottom-Up Approach**:
*Building the system from the ground up, starting with individual components.*

**Overview**:

*The **bottom-up approach** is the opposite of the top-down approach. It starts with the smallest, most basic units of the system and gradually combines them into larger structures. It's an incremental approach where the system is built from the ground up.*

**Steps**:
1. **Identify Basic Units**: Start with the smallest, fundamental components of the system.
2. **Build Components**: Develop each component independently.
3. **Integration**: Combine the developed components to create more complex structures.
4. **Achieve System Level**: Continue integrating until the entire system is constructed.

**Advantages**:
- **Early Results**: Allows for early prototypes and functional components.
- **Flexibility**: Easier to adapt to changes during development.

**Challenges**:
- **Integration Complexity**: Integrating various components can be challenging.
- **Possibility of Inconsistencies**: Lack of a holistic view initially might lead to inconsistencies.

### **Case Studies of Well-Designed Systems**

#### **Examples**:
- **Amazon Web Services (AWS)**:
    - **Overview**: AWS is a comprehensive cloud computing platform that provides a wide range of services, including computing power, storage, and databases.
    - **Design Highlights**: AWS is designed with a modular architecture, allowing users to choose and pay for only the services they need. It is highly scalable, and reliable, and provides a vast array of tools for developers.
- **Google's Infrastructure**:
    - **Overview**: Google's infrastructure supports a multitude of services, including search, Gmail, and Google Drive.
    - **Design Highlights**: Google's infrastructure is distributed, with data centers strategically located globally. It employs advanced algorithms for load balancing and fault tolerance, ensuring high availability and responsiveness.

#### **Analysis**:
Common Traits in Well-Designed Systems:
- **Modularity**: Both AWS and Google's infrastructure exhibit modularity by offering a range of services that can be independently utilized.
- **Scalability**: Scalability is a key feature in both systems. AWS allows users to scale resources up or down based on demand, and Google's infrastructure is designed to handle enormous amounts of data and user requests.
- **Reliability**: Reliability is a critical factor. Both systems have redundancy and fault-tolerance mechanisms in place to ensure uninterrupted service.
- **Flexibility**: Flexibility is evident in the customizable nature of services provided by AWS and the adaptability of Google's infrastructure to support various applications.

### Exercise | Requirement Analysis

####  **Scenario**: 
*Imagine you are tasked with designing a system for an online e-commerce platform that facilitates the buying and selling of various products. The platform aims to connect buyers with sellers, providing a seamless shopping experience. Your goal is to analyze and document the system requirements.*

#### **Tasks**

1. **Stakeholder Identification**:
    - **Definition**: Identify and list all stakeholders involved in the e-commerce platform.
    - **Example Stakeholders**: Customers (buyers), Sellers (vendors), Administrators, System Developers, Payment Processors, Customer Support
2. **Gathering and Analyzing Requirements**:
    - **Definition**: Use techniques like interviews, surveys, and research to gather detailed requirements.
    - **Example Techniques**:
        - **Interviews**: Conduct interviews with potential users to understand their needs and preferences.
        - **Surveys**: Distribute surveys to collect quantitative data on user expectations.
        - **Research**: Analyze existing e-commerce platforms and market trends.
3. **Prioritizing Requirements**:
    - **Definition**: Assign priorities to each requirement based on its importance to the success of the e-commerce platform.
    - **Example Criteria for Prioritization**:
        - **Critical Functionality**: Features essential for the core functionality of buying and selling.
        - **User Experience**: Enhancements that significantly improve the user experience.
        - **Market Trends**: Prioritize features aligned with current e-commerce market trends.
4. **Documenting Requirements**:
    - **Definition**: Create clear and concise documentation for each identified requirement.
    - **Example Documentation Template**:
        - **Requirement ID**: R001
        - **Description**: The system should allow registered users to add products to their shopping carts.
        - **Priority**: High
        - **Stakeholders**: Customers, Sellers
        - **Dependencies/Constraints**: Users must be registered and logged in to add products to the shopping cart.

### Solution

---
**Requirement ID**: R00001

**Description**: This system connects buyers and sellers, via a web-based application, where a buyer can buy multiple products using the web app from the seller.

**Priority**: High

**Stakeholders**: Customer (Buyer), Seller

**Dependencies/Constraints**: For this system to work, some products need to be present in the system and a logged-in, user can add the products and buy them from the seller.
1. user must be logged in, before buying
2. the seller must have added some products in the web app, to get the desired result.
---

## **Understanding System Requirements**

### **Architectural patterns**
*Architectural patterns in system design provide reusable solutions to common problems faced during the design and implementation of software systems. These patterns help structure and organize the code, making it more scalable, maintainable, and adaptable to changes.*

#### **Layered Architecture**:
- **Description**: *Divide the system into logical layers (e.g., presentation, business logic, data) with each layer responsible for a specific set of tasks.*
- **Advantages**: *Separation of concerns, modular design, and ease of maintenance.*

#### **Microservices Architecture**:
- **Description**: *Decomposes the system into small, independent services that communicate through APIs.*
- **Advantages**: *Scalability, independent deployment, technology diversity, and fault isolation.*

#### **Monolithic Architecture**:
- **Description**: *All components of the system are tightly integrated into a single codebase and deployed as a single unit.*
- **Advantages**: *Simplicity, easier to develop and test.*

#### **Event-Driven Architecture**:
- **Description**: *Components communicate through events, allowing for loose coupling and asynchronous communication.*
- **Advantages**: *Scalability, responsiveness, and adaptability to changes.*

#### **Service-Oriented Architecture (SOA)**:
- **Description**: *Organizes the system as a collection of services, each offering a specific business functionality.*
- **Advantages**: *Reusability, interoperability, and modularity.*

#### **Model-View-Controller (MVC)**:
- **Description**: *Separates the application into three interconnected components: Model (data and business logic), View (presentation layer), and Controller (handles user input).*
- **Advantages**: *Separation of concerns, maintainability, and reusability.*

#### **Repository Pattern**:
- **Description**: *Centralizes data access logic, providing a way to access data without exposing the underlying data store details.*
- **Advantages**: *Abstraction of data access, testability, and flexibility in choosing data storage technologies.*

#### **Proxy Pattern**:
- **Description**: *Provides a surrogate or placeholder for another object to control access or add functionality.*
- **Advantages**: *Controlled access, logging, and caching.*

#### **Publish-Subscribe Pattern**:
- **Description**: *Publishers emit messages to topics without knowing which subscribers consume them.*
- **Advantages**: *Loose coupling, independent scaling, and asynchronous event handling.*

#### **Dependency Injection**:
- **Description**: *Inverts the control of object creation and allows the creation of dependent objects to be moved outside the class that depends on them.*
- **Advantages**: *Testability, flexibility, and modularity.*

### **Requirements analysis**
**Requirements analysis** is a critical phase in system design, and a thorough understanding of stakeholder needs is essential for a successful design.

### **Stakeholder Identification and Analysis**

#### **Techniques for Stakeholder Identification**:

- **Brainstorming**:
    - **Process**: Gather a diverse group of people to generate a list of potential stakeholders.
    - **Benefits**: Encourages collective input and ensures a broad perspective.
- **Surveys and Questionnaires**:
    - **Process**: Distribute surveys to potential users, employees, and other involved parties.
    - **Benefits**: Collects feedback from a large audience, especially useful in large-scale projects.
- **Interviews**:
    - **Process**: Conduct one-on-one or group interviews with individuals representing different roles.
    - **Benefits**: Provides in-depth insights, and allows for clarification of roles and expectations.

#### **Importance of Understanding Stakeholder Perspectives**:
- **Diverse Needs**: Different stakeholders may have diverse needs and expectations from the system.
- **Conflict Resolution**: Understanding stakeholder perspectives helps in resolving conflicts and finding compromises.
- **Holistic Design**: A comprehensive understanding of stakeholders ensures a system that meets the requirements of all involved parties.

### **Requirements Gathering Techniques**

#### **Overview**:
*Requirements gathering is a critical step in system design, ensuring a thorough understanding of what the system needs to accomplish. Various techniques can be employed to gather requirements effectively.*

#### **Common Techniques**:

1. **Interviews**:
    - **Process**: Conduct one-on-one or group interviews with stakeholders to gather information.
    - **Benefits**: Provides detailed insights, allows for clarification, and builds a rapport with stakeholders.
2. **Surveys and Questionnaires**:
    - **Process**: Distribute structured surveys to a broad audience and collect responses.
    - **Benefits**: Gathers quantitative data, useful for large-scale user feedback.
3. **Observation**:
    - **Process**: Observe users in their natural environment to understand how they currently perform tasks.
    - **Benefits**: Offers insights into actual user behavior and identifies pain points.
4. **Workshops**:
    - **Process**: Bring together stakeholders for interactive sessions to discuss and define requirements.
    - **Benefits**: Encourages collaboration, captures diverse perspectives, and resolves potential misunderstandings.
5. **Prototyping**:
    - **Process**: Create a simplified model or prototype of the system to gather feedback.
    - **Benefits**: Allows stakeholders to interact with a tangible representation, uncovering additional requirements.

#### **Choosing the Right Technique**:
- **Nature of the Project**: The complexity and scale of the project influence the choice of technique.
- **Time Constraints**: Some techniques, like surveys, may be quicker to implement than workshops.
- **Accessibility of Stakeholders**: Availability and accessibility of stakeholders may determine the feasibility of certain techniques. 

### **Types of Requirements**

#### **Distinguishing between Functional and Non-functional Requirements**:
- **Functional Requirements**:
    - **Definition**: Describes what the system should do and the specific functionalities it should provide.
    - **Examples**:
        - Users should be able to create an account.
        - The system should allow users to add products to their shopping cart.
        - An admin should be able to manage user accounts.
- Non-functional Requirements:
    - **Definition**: Describes qualities or characteristics that the system should have, such as performance, security, and usability.
    - **Examples**:
        - The system should respond to user actions within 2 seconds.
        - Data should be encrypted during transmission.
        - The user interface should be intuitive and user-friendly.

#### **Importance of Both Types**:
- **Functional Requirements**:
    - Define the core features and capabilities of the system.
    - Directly contribute to the system's primary objectives.
- **Non-functional Requirements**:
    - Ensure the system's overall performance, security, and user experience.
    - Provide criteria for evaluating the success of the system.

### **Use Cases and User Stories**
**Introduction**:
*Use Cases and User Stories are powerful tools for capturing and expressing system requirements in a user-centric manner. They help in understanding how users interact with the system and the specific scenarios in which the system will be used.*

#### **Use Cases**:
- **Definition**: A use case is a description of how a user interacts with a system to accomplish a specific goal.
- **Components**:
    - **Actor**: A user or system that interacts with the system.
    - **System**: The main subject under discussion.
    - **Use Case**: Describes a specific interaction or flow of events.

**Example**:
- **Use Case**: The user makes a purchase.
- **Actor**: Customer
- **System**: E-commerce platform
- **Flow**:
    1. The customer adds items to the shopping cart.
    2. The customer proceeds to checkout.
    3. The customer provides shipping information.
    4. The customer completes the purchase.
#### **User Stories**:
**Definition**:
*A user story is a brief, simple description of a feature told from the perspective of the person who desires the functionality.*

- **Components**:
    - **Role**: The user or system role involved.
    - **Action**: What the user wants to do.
    - **Benefit**: The value or benefit the user gains.

**Example**:
- **User Story**: As a customer, I want to be able to track the delivery of my purchased items so that I know when to expect them.

### Exercise | Requirement Elicitation

#### **Scenario**: 
*You are now tasked with gathering requirements for an online banking system. The system aims to provide a secure and user-friendly platform for customers to manage their accounts, transfer funds, and view transaction history.*

#### **Tasks**:
1. **Stakeholder Identification**:
    - Identify and analyze stakeholders for the online banking system.
    - Consider both internal (bank employees) and external (customers) stakeholders.
2. **Requirements Gathering**:
    - Choose and justify a requirements-gathering technique for the online banking system.
    - Provide a sample set of questions or methods you would use in an interview or survey.
3. **Types of Requirements**:
    - List at least three functional and three non-functional requirements for the online banking system.
4. **Use Cases and User Stories**:
    - Create a use case or user story related to a fund transfer scenario in the online banking system.

### Solution

---
**Requirement ID**: R00002

**Description**: Requirement gathering for an online banking system.

**Stakeholders**: New Customers (Users who will open a new account with the bank), Existing Customers (Users who have already an account with the bank), Bank employees (who will manage and maintain the fund), and the Bank itself, which has the actual funds and user data.

**Dependencies/Constraints**:

1. The bank must have funds to run the bank
2. The bank also needs to have a management team.
3. User group that must have money and interest in the bank.

**Requirements Gathering**:

1. Describe the size of the bank and the user group on which the bank will be focused.
2. Feature:
    - Secure fund management
    - Secure user and their data management
    - User-friendly UI
    - viewing the transaction history
    - fund transfer to another bank account
    - new account creation
3. Security, use encryption and HTTPS

**Requirements**

- Functional Requirements
    1. Signup and Sign in
    2. View Transaction History
    3. Fund Transfer
- Non Functional Requirements
    1. Security of Data and Users
    2. User-friendly UI
    3. Fast and Efficient System

**Use Cases and User Stories**
Below is the complete journey
1. User A creates an account in the bank
2. Enters details of himself
3. user A submits some money to the bank.
4. user A checks the account balance
5. user A transfers some funds to the account of existing user B
6. user A and user B, both get notified about the money transfer
7. Both the users check the new account balance, also the updated transaction history.
---


## **System Architecture**

### **Introduction to System Architecture**

#### **Definition**: 
***System Architecture** refers to the high-level structure of a software system, defining how different components and modules interact with each other. It outlines the organization of a system, including hardware and software components, their relationships, and how they work together to achieve the system's objectives.*

#### **Importance**:

1. **Blueprint for the System**: It serves as a blueprint, providing a conceptual model of the entire system.
2. **Communication Tool**: It helps communicate the design and structure of the system to stakeholders.
3. **Foundation for Development**: It provides the foundation for the development team to build the system.

### **Key Components of System Architecture**

1. **Hardware Components**:
    - **Examples**: Servers, storage devices, and network infrastructure.
    - **Role**: Physical components that support the execution of software.
2. **Software Components**:
    - **Examples**: Operating systems, middleware, databases.
    - **Role**: Programs and applications that run on the hardware, enabling functionality.
3. **Network Components**:
    - **Examples**: Communication protocols, routers, and switches.
    - **Role**: Enable communication and data exchange between different system components.

### **Exercise | Designing System Architecture**

#### **Scenario**:
You are tasked with designing the system architecture for an e-commerce platform. The platform must handle a large number of concurrent users, provide fast response times, and ensure data security.

#### **Tasks**:
- **Identify Key Components**:
    - List the key hardware, software, and network components necessary for the e-commerce platform.
- **Choose an Architecture**:
    - Select an architecture type (e.g., Monolithic, Microservices, Client-Server) based on the requirements of the e-commerce platform.
    - Justify your choice with specific reasons.
- **Scalability and Performance**:
    - Propose strategies for ensuring scalability and high performance in the e-commerce platform's architecture.
    - Consider load balancing, caching, and other relevant techniques.
- **Documentation**:
    - Create a clear and concise document outlining the chosen architecture, key components, and scalability/performance considerations.

#### **Solution**:

---
- **Key Component**
    - **Hardware**
        1. **Server**:
            - **Role**: Physical machines or virtual instances, where the e-commerce web app will run
            - **Example**: Web servers, Application Server
        2. **Storage**:
            - **Role**: Data storage for web applications, database and file storage
            - **Example**: Relational Database, Object storage
    - **Software**:
        1. **Tech Stack**:
            - **Role**: This includes a programming language, framework and database
            - **Example**: Nodejs, Reactjs, MongoDB
        2. **Message Queue**:
            - **Role**: For asynchronous communication between different components
            - **Example: Apache Kafka for building event-driven architecture. 
    - **Network**:
        1. **Internal Connectivity**
            - **Role**: Network components for internal connectivity
            - **Example**: Router, Switches
- **Architecture**
    - **chosen architecture**: Microservices Architecture
    - **justification**: 
        1. **Scalability**: Microservices allow independent scaling for each service
        2. **Flexibility**: Customisation for each service allows flexibility
        3. **Fault tolerance**: An issue in one service, will not affect the other service working.
- **Scalability and Performance**
    - **Load balancing**: Distribute incoming network traffic on multiple servers to ensure optimal use of resources.
    - **Caching**: Use a cache system, to avoid extra load on the database.
    - **Asynchronous Processing**: Use message queues for asynchronous processing of tasks to improve system responsiveness
- **Documentation**:
    - **System Architecture Document**
        - **Overview**: Design a complete working E-commerce website. Users must be able to add a product and buy it.
    - **Key Component**
        - **Hardware**
            1. **Server**:
                - **Role**: Physical machines or virtual instances, where the e-commerce web app will run
                - **Example**: Web servers, Application Server
            2. **Storage**:
                - **Role**: Data storage for web applications, database and file storage
                - **Example**: Relational Database, Object storage
        - **Software**:
            1. **Tech Stack**:
                - **Role**: This includes a programming language, framework and database
                - **Example**: Nodejs, Reactjs, MongoDB
            2. **Message Queue**:
                - **Role**: For asynchronous communication between different components
                - **Example: Apache Kafka for building event-driven architecture. 
        - **Network**:
            1. **Internal Connectivity**
                - **Role**: Network components for internal connectivity
                - **Example**: Router, Switches
    - **Architecture**
        - **chosen architecture**: Microservices Architecture
        - **justification**: 
            1. **Scalability**: Microservices allow independent scaling for each service
            2. **Flexibility**: Customisation for each service allows flexibility
            3. **Fault tolerance**: An issue in one service, will not affect the other service working.
    - **Scalability and Performance**
        - **Load balancing**: Distribute incoming network traffic on multiple servers to ensure optimal use of resources.
        - **Caching**: Use a cache system, to avoid extra load on the database.
        - **Asynchronous Processing**: Use message queues for asynchronous processing of tasks to improve system responsiveness
---

## **Database Design**
*Database design serves as the backbone of a system, influencing its efficiency, scalability, and data integrity.*

### **Importance of Database Design**
*Database design is a critical aspect of system development, influencing the efficiency, reliability, and performance of the entire system.*

1. **Data Integrity**: Ensuring accuracy and consistency of data by avoiding redundancy and dependency issues.
2. **Efficient Retrieval**: Designing for efficient data retrieval and storage, particularly in scenarios with large datasets.
3. **Scalability**: Allowing the system to scale seamlessly as data volume and user interactions grow.
4. **Relationships**: Simplifying database maintenance tasks, reducing the likelihood of errors and improving overall system reliability.

### **Key Concepts in Database Design**

1. **Entity-Relationship (ER) Modeling**:
    - **Definition**: A visual representation of the relationships between different entities (objects) in the system.
    - **Purpose**: Helps define the structure of the database and how data entities are related.
    - **Practical Application**: Identify entities (e.g., User, Product, Order), and attributes, and establish relationships. For example, a User places multiple Orders.
2. **Normalization**:
    - **Definition**: A process of organizing data to eliminate redundancy and dependency issues.
    - **Purpose**: Reduces data anomalies, improves data integrity, and simplifies database maintenance.
    - **Practical Application**: Identify attributes for each entity and apply normalization rules to minimize data anomalies. For instance, ensuring that data is stored in the most efficient way possible, such as avoiding repeating groups.
3. **Indexing**:
    - **Definition**: Creating indexes on specific columns to speed up data retrieval operations.
    - **Purpose**: Enhances query performance by allowing the database engine to quickly locate and access relevant data.
    - **Practical Application**: Identify columns frequently used in queries and create indexes to optimize data access. For example, indexing on the "product_id" column for efficient product lookups

### **Exercise | Database Design - Entity-Relationship Modeling**

#### **Scenario**:
You are tasked with designing the database for the e-commerce platform discussed in the previous exercise. The database should capture information about users, products, orders, and transactions.

#### **Tasks**:
- **Identify Entities**:
    - List the main entities relevant to the e-commerce platform (e.g., User, Product, Order).
- **Define Relationships**:
    - Establish relationships between entities (e.g., A User can place multiple Orders).
- **Attributes and Data Types**:
    - Identify key attributes for each entity and define their data types (e.g., User has attributes like username, email, password).
- **Normalization**:
    - Apply normalization techniques to eliminate redundancy and dependency issues.

### Solution

---
- **Identify Entities**:
    1. **User**
    2. **Product**
    3. **Order**
    4. **Transaction**
    5. **Payment Mode**
    6. **Aggregator**
    7. **COD Data**
    8. **Product Level COD DATA**
- **Define Relationships**:
    - **User** relates with
        - **Order**: User A, placed an order with order_id as `ord0000001`
        - **Transaction**: User A, paid some amount with transacton_id as `TR0000001`
        - **COD Data**: User A, has COD data, such as cod order limit  with id as `COD0000001`
    - **Product** relates with
        - **Product Level COD DATA**: Product P, has COD data such as product level cod charges
    - **Order** relates with
        - **User**: Order is placed by User
        - **Product**: The order contains a list of product IDs, which were part of the order
        - **Transaction**: Order payments are linked with a transaction
        - **COD Data**: If COD order, all details for COD order linked
    - **Transaction**: relates with
        - **User**: Each transaction is linked with a user
        - **Order**: Each transaction is linked with an order
        - **Payment Mode** Each transaction is linked with a payment mode.
    - **Payment Mode**: relates with
        - **Aggregator** Each payment mode is powered by an aggregator.
    - **Aggregator**: relates with
        - **Payment Mode**: Each payment mode is linked to an aggregator
    - **COD Data** relates with
        - **User**: Each user is linked with COD Data
        - **Order**: Order is linked to COD Data if a COD order were placed
    - **Product Level COD DATA**
        - **Product**: Product level COD Data
- **Attributes and Data Types**:
    1. **User**
        - user_id: String
        - name: String
        - email: String
        - phone_number: String
        - user_cod_id: String
    2. **Product**
        - product_id: String
        - product_name: String
        - product_price: Float
        - prouct_cod_id: String
    3. **Order**
        - order_id: String
        - transaction_id: String
        - user_id: String
        - amount: Float
        - order_time: Datetime
        - product_ids: String
    4. **Transaction**
        - transaction_id: String
        - order_id: String
        - user_id: String
        - amount: Float
        - is_cod: boolean
        - payment_mode_id: Integer
    5. **Payment Mode**
        - payment_mode_id: Integer
        - payment_mode_name: String
        - aggregator_id: Integer
    6. **Aggregator**
        - aggregator_id: Integer
        - aggregator_name: String
        - is_active: boolean
    7. **COD Data**
        - cod_id: String
        - cod_limit: Float
        - user_id: String
    8. **Product Level COD DATA**
        - prouct_cod_id: String
        - cod_limit: Float
- **Normalization**
    - Already in Normalized form
---

## **RESTful APIs (Representational State Transfer)**
*RESTful APIs are a set of principles and constraints that guide the design of web services. Following these principles helps in creating scalable, maintainable, and interoperable APIs.*

Here are the key RESTful API principles and best practices:

### **RESTful API Principles**:
- **Resource-Based**:
    - **Principle**: Resources are the key abstractions in a RESTful API. They should be identified by URIs, and clients can interact with them using standard HTTP methods (GET, POST, PUT, DELETE).
- **Uniform Interface**:
    - **Principle**: A uniform and consistent interface simplifies communication between clients and servers. It includes four constraints:
        - **Identification of Resources**: Resources are uniquely identified using URIs.
        - **Manipulation of Resources through Representations**: Clients interact with resources through representations, such as JSON or XML.
        - **Self-Descriptive Messages**: Each message from the server includes information about how to process it.
        - **Hypermedia as the Engine of Application State (HATEOAS)**: The server provides links dynamically to guide the client through the application.
- **Stateless**:
    - **Principle**: Each request from a client contains all the information the server needs to fulfill the request. The server does not store any client state between requests.
- **Client-Server Architecture**:
    - **Principle**: The client and server are separate entities that communicate over a stateless protocol (usually HTTP). This separation allows them to evolve independently.
- **Cacheability**:
    - **Principle**: Responses from the server can be marked as cacheable or non-cacheable. This improves performance by allowing clients to cache responses.
- **Layered System**:
    - **Principle**: The architecture can be composed of multiple layers, where each layer has a specific responsibility. Layers can be added, removed, or modified without affecting the system as a whole.

### **RESTful API Best Practices**:
- **Use Nouns for Resource Names**: *Choose resource names that are nouns and represent the entities in your system. For example, use "/users" to represent a collection of users.*
- **Use Plural Nouns for Collection Resources**: *For resource collections, use plural nouns to represent the collection. For example, "/products" for a collection of products.*
- **Use HTTP Methods Appropriately**: *Use HTTP methods (GET, POST, PUT, DELETE) according to their semantics. For example, use GET for retrieving resources, POST for creating resources, PUT for updating resources, and DELETE for deleting resources.*
- **Versioning**: *Consider versioning your API to provide backward compatibility as your API evolves. Use version numbers in the URI or headers.*
- **Filtering, Sorting, and Pagination**: *Provide mechanisms for clients to filter, sort, and paginate results to improve efficiency and usability.*
- **Consistent Endpoint Naming**: *Maintain consistency in your endpoint naming conventions. Similar resources and operations should have similar naming patterns.*
- **Use HTTP Status Codes**: *Use appropriate HTTP status codes to indicate the success or failure of a request. For example, use 200 OK for successful requests, 404 Not Found for not found resources, and 201 Created for successful resource creation.*
- **Provide Error Handling**: *Include detailed error messages in the response to help clients diagnose issues. Use standard error formats like JSON API or Problem Details for HTTP APIs.*
- **Security**: *Implement secure practices, including authentication and authorization mechanisms. Use HTTPS to encrypt data in transit.*
- **Documentation**: *Provide clear and comprehensive documentation for your API, including information on available endpoints, request and response formats, and examples.*
- **Rate Limiting**: *Implement rate limiting to prevent abuse and ensure fair usage of your API resources.*
- **Testing and Monitoring**: *Regularly test your API, and implement monitoring to track usage patterns and identify potential issues.*

*By adhering to these RESTful API principles and best practices, you can create APIs that are scalable, maintainable, and easy for developers to work with.*

## **Security in System Design**

### **Importance of Security in System Design**

*Security is a critical aspect of system design, protecting against potential threats and ensuring the confidentiality, integrity, and availability of data.*

#### **CIA | Confidentiality, Integrity, Availability**
- **Confidentiality**:
Protecting sensitive information from unauthorized access.
- **Integrity**:
Ensuring that data remains accurate and unaltered.
- **Availability**:
Guaranteeing that the system and its resources are available when needed.

### **Key Concepts in System Security**

#### **Authentication**
*Authentication is the process of verifying the identity of a user, system, or device.*

- **Methods**:
    - **Passwords**: Traditional but should be strong and secure.
    - **Biometrics**: Fingerprint, facial recognition.
    - **Two-Factor Authentication (2FA)**: Adds an extra layer of security.

#### **Authorization**
*Authorization is the granting of access rights to authenticated users based on their roles and permissions.*

- **Implementation**:
    - **Role-based Access Control (RBAC)**: Assigns permissions based on user roles.
    - **Access Control Lists (ACLs)**: Lists specifying user permissions for specific resources.

#### **Encryption**:
*Encryption involves converting data into a secure format to prevent unauthorized access.*

- **Types**:
    - **Symmetric Encryption**: Uses a single key for both encryption and decryption.
    - **Asymmetric Encryption**: Utilizes a pair of public and private keys.

### **Exercise | Security in System Design**

#### **Scenario**:

*Enhance the security of the e-commerce platform by identifying potential security threats and proposing measures to mitigate risks.*

#### **Tasks**:

- **Identify Security Threats**:
    - List potential security threats (e.g., unauthorized access, data breaches).
- **Authentication Measures**:
    - Propose authentication methods to ensure only legitimate users access the system.
- **Authorization Strategies**:
    - Define authorization strategies to control access rights based on user roles.
- **Encryption Techniques**:
    - Specify encryption techniques to secure sensitive data during transmission and storage.

### **Solution**

---
- **Security Threats**:
    - Unauthorized access to the database will cause
        - order data issue
        - aggregator data issue
        - product pricing issue
        - cod limit issue
    - Data breach to the database will cause
        - leak of private information about users 
        - leak of aggregator credentials
        - leak of orders made by the customer
- **Authentication Measures**:
    - Access to the database must be password-protected
- **Authorization Strategies**:
    - Read and Write access must be maintained via RBAC and ACLs
- **Encryption Techniques**:
    - user data and aggregator data must be encrypted to avoid issues in case of a data breach
---

## **Scalability in System Design**

### **Importance of Scalability in System Design**

#### **Significance**
*Scalability is crucial in system design to ensure that a system can handle increasing loads and demands. It involves designing a system that can grow and adapt to accommodate a larger number of users, transactions, or data volume.*

#### **Types of Scalability**
- **Vertical Scalability**:
*This involves scaling up by adding more resources to a single machine. For example, upgrading a server's RAM, CPU, or storage. While it's a straightforward approach, it has limits, and there's a point where further vertical scaling becomes impractical or costly.*

- **Horizontal Scalability**:
*This involves scaling out by adding more machines or nodes to a system. It's a more flexible approach as it allows for distributing the load across multiple servers, enhancing overall system capacity.*

#### **Scaling in depth**:
- **When to Choose Vertical Scaling**: Vertical scaling involves adding more resources to a single machine, such as increasing CPU or RAM. While this can be effective, it has limitations. Understanding when it's suitable involves considering factors like the potential for resource saturation and cost-effectiveness.

- **Challenges of Horizontal Scaling**: Horizontal scaling, where you add more machines to your system, introduces challenges. Ensuring data consistency across distributed nodes and managing network overhead are critical considerations.

- **Dynamic Scaling Strategies**: Exploring strategies for dynamic scaling, where resources are added or removed based on real-time demand. This involves a thorough understanding of workload patterns and efficient load prediction algorithms.

- **Scalability for Different Components**: Recognizing that scalability requirements can vary for different components of a system. For example, a web server might need different scaling strategies than a database server.


### **Key Concepts in Scalability**
#### **Load Balancing**:
- **Definition**: *Load balancing distributes incoming network traffic across multiple servers to ensure no single server is overwhelmed, optimizing resource utilization.*

- **Methods**:
    1. **Round Robin**: This method distributes traffic equally, ensuring a fair allocation of requests among servers.
    2. **Least Connections**: This method directs traffic to the server with the fewest active connections, optimizing resource usage.
- **Importance**: Load balancing is essential for achieving both vertical and horizontal scalability, preventing bottlenecks and optimizing resource utilization.

**Load Balancing in Depth**:
- **Load Balancing Algorithms**: Going beyond the basics, understanding the intricacies of load balancing algorithms is crucial. For example, Weighted Round Robin considers server capacity, ensuring that more powerful servers handle a larger share of the load. Least Connections, on the other hand, directs traffic to the server with the fewest active connections, optimizing resource utilization.

- **Dynamic Load Balancing**: Delving into dynamic load balancing, where algorithms adjust based on server health and performance metrics. This involves considerations such as the frequency of adjustments and the threshold for triggering a rebalance.

- **Identify Scalability Challenges**:
    - **Predictive Scaling**: Going beyond identifying current scalability challenges, exploring predictive scaling involves using historical data and machine learning algorithms to anticipate future scaling needs. This can include peak usage periods or unexpected traffic spikes.

    - **Workload Modeling**: Understanding the importance of workload modeling, where the system is subjected to simulated loads to assess its behavior under different conditions. This involves creating realistic scenarios that mimic actual usage patterns.

- **Load Balancing Strategy**:
    - **Elastic Load Balancers**: Evaluating cloud-based load balancing solutions, such as Elastic Load Balancers in cloud platforms like AWS. Understanding the advantages of these services, such as automatic scaling and integrated health checks.

    - **Global Load Balancing**: Exploring global load balancing strategies for distributed systems with servers in multiple geographical locations. This involves considerations like DNS-based load balancing and latency-based routing.

#### **Caching**:
- **Definition**: *Caching involves storing copies of frequently accessed data in a cache to reduce the need to retrieve the same data from the source.*

- **Benefits**:
    - **Faster data retrieval**: By keeping frequently accessed data closer to the user, response times are significantly reduced.
    - **Reduced load on databases**: Caching alleviates the strain on databases, especially during peak usage periods, contributing to improved overall system performance.
- **Caching Strategies**:
    - **Content Delivery Network (CDN)**: Distributes cached content across multiple servers globally.
    - **In-Memory Caching**: Stores data in the server's memory for rapid access.

- **Caching in Depth**
    - **Cache Invalidation Strategies**: Going beyond the basics of caching benefits, understanding how to handle cache invalidation is critical. Invalidation strategies involve determining when and how to refresh or remove cached data to maintain consistency.

    - **Cache Partitioning**: Delving into advanced cache partitioning techniques, where the cache is divided into segments. This can involve strategies such as sharding the cache based on data characteristics or access patterns. Efficient cache partitioning optimizes utilization and reduces data duplication.

#### **Database Sharding**:
- **Definition**: *Database sharding involves breaking a large database into smaller, more manageable parts called shards, and distributing the data across multiple servers.*

- **Advantages**:
    - **Improved query performance**: Smaller datasets per shard result in faster query execution times.
    - **Enhanced system scalability**: As the number of shards increases, the system's overall capacity to handle data and transactions grows.
- **Sharding Strategies**:
    - **Range-Based Sharding**: Divides data based on a specified range of values (e.g., user IDs).
    - **Hash-Based Sharding**: Distributes data across shards using a hash function.

- **Database sharding in Depth**
    - **Dynamic Sharding**: Instead of static sharding, explore dynamic sharding strategies where the system adapts to changing data patterns. This might involve automated tools that analyze data distribution and adjust sharding configurations accordingly.

    - **Transparent Sharding**: Understanding how transparent sharding allows the application to interact with the database without explicit knowledge of sharding. This involves a layer that manages the distribution of data across shards without impacting the application's logic.

- **Database Sharding Plan**:
    - **Automated Sharding**: Going deeper into automated sharding tools and their role in maintaining optimal data distribution. Automated sharding involves not only initial configuration but also continuous monitoring and adjustment based on evolving data patterns.

    - **Shard Key Selection**: Delving into the importance of selecting an appropriate shard key. The choice of a shard key significantly influences the efficiency of data distribution and retrieval. Factors such as cardinality, access patterns, and potential hotspots should be considered.

#### **Identify Scalability Challenges**:
- **Predictive Scaling**: Expanding on predictive scaling, understanding the role of machine learning algorithms. These algorithms analyze historical data, identify patterns, and predict future scaling needs. This involves considerations like algorithm accuracy, model training, and adapting to changing workloads.

- **Workload Modeling**: Going deeper into workload modeling techniques, including scenarios with burst traffic or sudden spikes. Advanced workload modeling involves simulating complex scenarios to assess the system's responsiveness and resource utilization under diverse conditions.

### **Exercise | Scalability in System Design**

#### **Scenario**:
*Enhance the scalability of the e-commerce platform to handle a growing number of users and transactions.*

#### **Tasks**:
- **Identify Scalability Challenges**:
    - List potential scalability challenges for the e-commerce platform (e.g., increased user traffic, growing database size).

- **Load Balancing Strategy**:
    - Propose a load-balancing strategy to distribute incoming traffic effectively.

- **Caching Implementation**:
    - Specify how caching can be implemented to improve system performance.

- **Database Sharding Plan**:
    - Outline a plan for implementing database sharding to address scalability challenges.

#### **Solution**
---
- **Identify Scalability Challenges**
    - Onboarding new users can cause system failures
    - Onboarding new sellers on our system may cause slow loading
    - onboarding new aggregators for payment gateways may cause slow payment

- **Load Balancing Strategy**:
*Onboarding new users can lead to more traffic on the system*
    - Sale time: Least Connections, is best
    - Normal time: Round Robin, is best

- **Caching Implementation**
    - as there are multiple aggregators, payment options for each aggregator can vary, so putting the payment option in the cache is a better option

- **Database Sharding Plan**
    - **Geographical Database sharding** as users may be from different geolocation, data sharding based on geolocation, is a better option.
---

## **Microservices Architecture**

### **Fundamentals of Microservices**

**Significance**:
*Understanding the fundamental principles of microservices architecture is essential for designing scalable and maintainable systems*

- **Decomposition Strategies**:
    - **Domain-Driven Design (DDD)**: Going beyond basic decomposition, exploring how DDD principles guide the identification of microservices based on business domains. Understanding bounded contexts, aggregates, and entities enhances the precision of decomposition.

    - **Strangler Pattern**: Delving into the Strangler pattern as a migration strategy. This involves gradually replacing monolithic components with microservices, allowing for incremental and low-risk transitions.

- **Service Independence**:
    - **Data Independence**: Understanding how microservices achieve data independence through separate databases or database schemas. This involves considerations such as data consistency across services and the role of event-driven architectures in maintaining eventual consistency.

    - **Communication Protocols**: Exploring communication protocols between microservices. In addition to RESTful APIs, understanding when to use messaging protocols (e.g., Kafka or RabbitMQ) for asynchronous communication and event-driven architectures.

### **Challenges and Best Practices**

#### **Scalability Challenges**

1. **Practical Implications**:
    - **Service Discovery**: Going beyond basic service discovery mechanisms, exploring advanced strategies such as dynamic service discovery. This involves tools like *Consul*, which dynamically updates service registries based on real-time changes in the infrastructure.

    - **Resilience Strategies**: Delving into advanced resilience strategies, including circuit breakers, bulkheads, and retries. Understanding how these patterns contribute to system stability under varying conditions.

2. **Best Practices in Microservices Design**

    - **Implementation Strategies**: 
        - **Event Sourcing**: Going deeper into event sourcing as a data storage and communication pattern. Understanding the benefits and challenges of capturing and storing events for maintaining the state of microservices.

        - **Container Orchestration**: Exploring container orchestration platforms like Kubernetes and their role in managing and scaling microservices. Understanding deployment strategies, rolling updates, and service scaling in containerized environments.

### **Data Management in Microservices**

**Significance**: *Effective data management is crucial for microservices architecture, ensuring data consistency, availability, and scalability.*

#### **Data Consistency Strategies**:
- **Eventual Consistency**:  Eventual consistency, a cornerstone in distributed systems, acknowledges that, in certain scenarios, achieving immediate consistency across all microservices is impractical. It allows systems to prioritize availability and partition tolerance. For example, when a user updates their profile picture, it may take a short period for the change to propagate across all services. Eventual consistency strategies include conflict resolution and versioning to manage data consistency over time.

- **Transaction Patterns**: Traditional distributed transactions face challenges in microservices due to their impact on scalability and autonomy. Instead, the Saga pattern is often employed. A saga represents a sequence of local transactions, each updating the data within a microservice, and the overall consistency is maintained through a series of compensating transactions if a failure occurs at any step.

#### **Data Ownership and Autonomy**:
- **Data Ownership**: In microservices, each service is responsible for its data. This concept of data ownership aligns with the autonomy of microservices, allowing teams to make independent decisions about their data models and storage technologies. This approach reduces dependencies between services but requires clear communication and API contracts.

- **Autonomous Databases**: Microservices often benefit from having dedicated databases, ensuring autonomy and isolation. Each microservice can choose the database that best suits its requirements. This autonomy enhances the scalability and resilience of the overall system.

### **Security in Microservices**
**Significance**: *Ensuring the security of microservices is paramount to protecting sensitive data and maintaining system integrity*

#### **Authentication and Authorization**:
- **Token-Based Authentication**: Microservices commonly utilize token-based authentication, employing technologies like JWT or OAuth. When a user logs in, they receive a token that includes information about their identity and permissions. Subsequent requests include this token for secure communication between microservices.

- **Fine-Grained Authorization**: Fine-grained authorization allows services to define access control at a granular level. Each microservice specifies the level of access it requires, ensuring that only authorized services can interact with specific data. This approach enhances security by limiting exposure and potential vulnerabilities.

#### **Secure Communication**:
- **Transport Layer Security (TLS)**: Secure communication between microservices is established through Transport Layer Security (TLS). This encryption protocol ensures data privacy and integrity during transit. It mitigates the risk of eavesdropping and man-in-the-middle attacks, safeguarding sensitive information.

- **API Gateway Security**: API gateways act as a security perimeter for microservices. They enforce policies such as rate limiting, authentication, and input validation. This centralized approach enhances security measures and simplifies the implementation of consistent security policies across microservices.

## **Event-Driven Architecture**

### **Principles of Event-Driven Architecture**

**Significance**: *Understanding the principles of event-driven architecture is crucial for designing responsive and decoupled systems*

- **Event Sourcing**:
    - **Event Log**: An event log captures all state-changing events in a system, providing a historical record to reconstruct the system's state.
    - **CQRS (Command Query Responsibility Segregation)**: CQRS separates handling commands that update the system state from queries that retrieve information, optimizing read and write operations independently.

- **Asynchronous Communication**:
    - **Message Brokers**: Message brokers (e.g., Kafka, RabbitMQ) enable asynchronous communication, facilitating the decoupling of components.
    - **Event-driven Microservices**: Events serve as the communication mechanism between microservices, promoting loose coupling and enhancing scalability.

### **Implementation Challenges and Best Practices**
- **Challenges in Event-Driven Architecture**:
    - **Practical Implications**:
        - **Eventual Consistency**: Achieving eventual consistency in event-driven systems poses practical challenges. Strategies are needed to handle these challenges without compromising system reliability.

    - **Event Schema Evolution**: Evolving event schemas over time introduces challenges. Managing these changes requires strategies to ensure backward and forward compatibility.

- **Best Practices in Event-Driven Architecture**:
    - **Implementation Strategies**:
        - **Idempotency**: Designing systems with idempotency ensures reliable event processing by handling duplicate events without unintended side effects.
        - **Event Versioning**: Best practices for event versioning ensure backward and forward compatibility, allowing systems to evolve without disrupting existing components.

## **System Monitoring and Performance Optimization**

### **Importance of System Monitoring**

**Significance**: *Understanding the importance of system monitoring is crucial for maintaining system health and identifying performance bottlenecks*

- **Real-time Visibility**:
    - **Monitoring Tools**: Utilizing monitoring tools to gain real-time visibility into system components. Tools like Prometheus or Grafana allow tracking metrics, logging, and tracing for comprehensive insights.

    - **Alerting Mechanisms**: Implementing alerting mechanisms based on predefined thresholds to notify administrators of potential issues promptly.

- **Performance Metrics**:
    - **Key Performance Indicators (KPIs)**: Identifying and tracking key performance indicators, such as response time, throughput, and error rates. Monitoring these metrics provides a holistic view of system performance.

    - **Resource Utilization**: Tracking resource utilization metrics (CPU, memory, disk I/O) to identify potential bottlenecks and optimize resource allocation.

### **Performance Optimization Strategies**
**Significance**: *Implementing performance optimization strategies is essential for delivering a responsive and scalable system*

- **Code Optimization**:
    - **Profiling Tools**: Using profiling tools to identify performance bottlenecks in the code. Tools like YourKit or VisualVM help analyze code execution and identify areas for improvement.

    - **Algorithmic Efficiency**: Optimizing algorithms for better efficiency. Choosing algorithms with lower time complexity can significantly impact system performance.

- **Infrastructure Scaling**:
    - **Horizontal Scaling**: Scaling horizontally by adding more instances to distribute the load. This approach enhances system resilience and responsiveness.

    - **Vertical Scaling**: Scaling vertically by increasing the resources of existing instances. Understanding when to scale vertically based on resource needs.

- **Load Testing and Capacity Planning**
**Significance**: *Load testing and capacity planning are critical for ensuring the system can handle expected workloads*

- **Load Testing**:
    - **Simulating User Load**: Using tools like Apache JMeter or Locust to simulate realistic user loads and identify how the system performs under different scenarios.

    - **Stress Testing**: Conducting stress testing to determine system limits and potential points of failure under extreme conditions.

- **Capacity Planning**:
    - **Resource Prediction**: Predicting resource needs based on expected growth. Understanding how the system's capacity aligns with future demands.

    - **Scalability Assessment**: Assessing the system's scalability by analyzing how it handles increased loads and identifying areas for improvement.

## **Cloud-Native Architecture**

### **Fundamentals of Cloud-Native Architecture**
**Significance**: *Understanding the fundamentals of cloud-native architecture is crucial for leveraging cloud services effectively*

- **Microservices in the Cloud**:
    - **Containerization**: Utilizing containers (e.g., Docker) for packaging and deploying microservices. Containers provide consistency across different environments and simplify deployment.

    - **Orchestration**: Implementing orchestration tools (e.g., Kubernetes) to automate the deployment, scaling, and management of containerized applications. Orchestration enhances efficiency and ensures high availability.

- **Serverless Computing**:
    - **Event-Driven Execution**: Embracing serverless computing for event-driven execution. Functions as a Service (FaaS) platforms (e.g., AWS Lambda) allow running code in response to events, eliminating the need for traditional server management.

    - **Scalability and Cost Optimization**: Leveraging serverless computing for automatic scalability and cost optimization. Paying only for the actual compute resources consumed during execution.

### **Cloud-Native Best Practices**

**Significance**:
*Adopting cloud-native best practices is essential for building resilient and scalable systems*

- **Decentralized Data Management**:
    - **Distributed Databases**: Implementing distributed databases for decentralized data management. This approach ensures data availability and resilience even if individual components fail.

    - **Data Caching**: Utilizing caching mechanisms (e.g., Redis) to enhance data retrieval performance and reduce the load on backend services.

- **Resilience and Fault Tolerance**:
    - **Chaos Engineering**: Embracing chaos engineering principles to proactively identify system weaknesses. Simulating failures allows an understanding of how the system behaves under adverse conditions.

    - **Automated Recovery**: Implementing automated recovery mechanisms to minimize downtime. Strategies include automatic scaling, rolling updates, and self-healing systems.

### **Cloud-Native Security**

**Significance**: *Ensuring cloud-native security is paramount for protecting data and maintaining system integrity*

- **Identity and Access Management (IAM)**:
    - **Role-Based Access Control (RBAC)**: Implementing RBAC for fine-grained access control. Assigning permissions based on roles ensures that users have the necessary access without unnecessary privileges.

    - **Multi-Factor Authentication (MFA)**: Enforcing MFA to add an extra layer of security. Authenticating users through multiple factors reduces the risk of unauthorized access.

- **Network Security**:
    - **Virtual Private Cloud (VPC)**: Using VPCs to isolate resources and control network traffic. VPCs provide a secure and isolated environment within the cloud infrastructure.

    - **Security Groups and Network ACLs**: Configuring security groups and network ACLs to control inbound and outbound traffic. These measures enhance the security posture of cloud-native applications.


## **DevOps and Continuous Integration/Continuous Deployment (CI/CD)**

### **Overview of DevOps**

#### **Definition and Principles**
*DevOps is a cultural and professional movement that stresses communication, collaboration, and integration between software developers and IT operations. The main goal is to automate the process of software delivery and infrastructure changes while ensuring high reliability, stability, and performance.*

**Key principles include**:

- **Collaboration**: *Breaking down silos and fostering collaboration between development and operations teams to streamline workflows and communication.*

- **Automation**: *Automating manual processes, such as testing and deployment, to enhance efficiency, reduce errors, and accelerate the delivery pipeline.*

- **Continuous Integration**: Developers regularly integrate their code into a shared repository, where automated builds and tests are performed. This ensures that changes are quickly identified and addressed.

- **Continuous Deployment**: Automatically deploy code changes to production or staging environments after successful testing, allowing for faster and more frequent releases.

- **Monitoring and Feedback**: Continuous monitoring of applications and infrastructure, coupled with feedback loops, helps identify issues early and facilitates continuous improvement.

**DevOps Best Practices**
- **Automation**: Automate repetitive tasks, including testing, deployment, and infrastructure provisioning.

- **Collaboration**: Foster a culture of collaboration and shared responsibility between development and operations teams.

- **Monitoring and Logging**: Implement robust monitoring and logging practices to detect issues early and troubleshoot effectively.

- **Security Integration**: Embed security practices into the DevOps pipeline to address vulnerabilities throughout the development lifecycle.

- **Scalability Planning**: Plan for scalability from the outset, anticipating growth and adjusting resources accordingly.

**Benefits of DevOps in System Development**

- **Increased Deployment Frequency**: DevOps practices enable organizations to release software updates more frequently, responding rapidly to user feedback and market demands.

- **Faster Time to Market**: Automation and collaboration reduce the time it takes to develop, test, and deploy software, enabling organizations to bring new features and improvements to market swiftly.

- **Lower Failure Rate of New Releases**: Automated testing and continuous monitoring help catch issues early in the development process, resulting in more stable and reliable releases.

- **Shortened Lead Time Between Fixes**: Quick identification and resolution of issues mean a shorter time between identifying a problem and deploying a fix.

### **Continuous Integration (CI) and Continuous Deployment (CD)**
#### **Continuous Integration (CI)**
**Definition**: *Continuous Integration is a development practice where code changes from multiple contributors are automatically integrated into a shared repository several times a day.*

**Key Practices**:
- **Automated Builds**: *Code changes trigger automated build processes to ensure compilation and basic correctness.*
- **Automated Tests**: *Comprehensive test suites (unit tests, integration tests) are run automatically to detect regressions.*

**Benefits**:
- **Early Detection of Bugs**: CI helps catch bugs and integration issues early in the development process.
- **Faster Feedback Loop**: Developers receive prompt feedback on the impact of their changes.
- **Improved Collaboration**: Integration issues are resolved continuously, promoting collaboration.

**Popular CI Tools**:
- **Jenkins**
- **Travis CI**
- **CircleCI**

#### **Continuous Deployment (CD)**
**Definition**: *Continuous Deployment is an extension of CI where code changes that pass automated tests are automatically deployed to production.*

**Key Practices**:
- **Automated Deployment**: *Successful CI builds trigger automated deployment to production environments.*
- **Feature Flags**: *Features can be toggled on/off via feature flags, allowing safe experimentation.*
- **Rollback Strategies**: *Automated rollback mechanisms in case of issues.*

**Benefits**:
- **Rapid Delivery**: *Continuous Deployment enables frequent and rapid releases.*
- **Lower Deployment Risk**: *Automation reduces the risk of human error during deployment.*
- **Real-time User Feedback**: *Users receive new features and bug fixes faster.*

**Popular CD Tools**:
- **Spinnaker**
- **GitLab CI/CD**
- **AWS CodePipeline**

### **CI/CD Pipeline**

#### **Building a CI/CD Pipeline**
*A CI/CD pipeline is a series of automated steps that facilitate the integration, testing, and deployment of code changes.*

It typically consists of the following stages:

- **Code Commit**: Developers commit their changes to a version control system (e.g., Git).

- **Continuous Integration**: Automated build and test processes are triggered whenever changes are committed, ensuring that new code integrates successfully with the existing codebase.

- **Artifact Storage**: The compiled application code and dependencies are stored as artifacts that can be used for deployment.

- **Continuous Deployment**: The artifacts are deployed to staging or production environments automatically after passing tests in the continuous integration phase.

#### **Automated Testing and Deployment**
- **Automated Testing**: Various types of automated tests, including unit tests, integration tests, and end-to-end tests, are executed to validate the functionality and quality of the code.

- **Automated Deployment**: Once the code changes pass all tests, the CI/CD pipeline automatically deploys the application to the target environment. This can involve deploying to staging for further testing before moving to production.

#### **Practical Implementation**
Successful implementation of DevOps and CI/CD involves:

- **Version Control**: Using a robust version control system (e.g., Git) to manage and track changes to the codebase.

- **Automation Tools**: Employing automation tools for building, testing, and deployment, such as Jenkins, Travis CI, or GitLab CI.

- **Infrastructure as Code (IaC)**: Treating infrastructure as code allows the automated provisioning and management of infrastructure using scripts, ensuring consistency and scalability.

- **Monitoring and Logging**: Implementing monitoring and logging solutions to gain insights into the performance and health of applications and infrastructure.

- **Collaboration Platforms**: Utilizing collaboration platforms to enhance communication and coordination among team members.

- **Security Measures**: Integrating security practices into the CI/CD pipeline to identify and address vulnerabilities early in the development process.

*Implementing DevOps and CI/CD is an ongoing process of refinement and improvement, with a focus on continuous learning and adaptation to changing requirements.*

### **Infrastructure as Code (IaC)**
**Definition and Importance**
*Infrastructure as Code (IaC) is a key practice in DevOps that involves managing and provisioning computing infrastructure through machine-readable script files, rather than physical hardware configuration or interactive configuration tools. The core idea is to treat infrastructure—servers, databases, networks—as code, enabling automated and repeatable processes for deployment.*

**Infrastructure as Code (IaC) in DevOps**
- **Integration with CI/CD**: *IaC is a crucial aspect of DevOps, allowing infrastructure changes to be versioned, tested, and deployed automatically.*

- **Continuous Monitoring**: *DevOps emphasizes continuous monitoring of infrastructure and applications to detect issues and ensure optimal performance.*

- **Collaboration and Communication**: *DevOps promotes collaboration and communication between development, operations, and other stakeholders, fostering a culture of shared responsibility.*

- **Feedback Loops**: *Short feedback loops are established, enabling quick responses to changes, issues, and user feedback.*

#### **Key Concepts and Practices**
- **Declarative vs. Imperative**: IaC scripts can be declarative or imperative. Declarative IaC focuses on the desired end state, while imperative IaC specifies the steps to reach that state.

- **Idempotency**: IaC scripts are designed to be idempotent, meaning that applying the script multiple times produces the same result as applying it once. This ensures consistency and reliability.

- **Version Control for Infrastructure**: Storing IaC scripts in version control systems allows teams to track changes, roll back to previous states, and collaborate effectively.

- **Infrastructure Provisioning Tools**: Tools like Terraform, AWS CloudFormation, and Ansible are commonly used for IaC. These tools provide a framework for defining and provisioning infrastructure components.

#### **Practical Implementation**

- **Terraform**: Terraform is a popular IaC tool that uses a declarative language to define and provision infrastructure. It supports multiple cloud providers and on-premises environments.

    *Example Terraform script for provisioning an AWS S3 bucket*
    ```tf
    provider "aws" {
        region = "us-west-2"
    }

    resource "aws_s3_bucket" "my_bucket" {
        bucket = "my-unique-bucket-name"
        acl    = "private"
    }
    ```

- **Ansible**: Ansible is an imperative IaC tool that uses YAML to describe automation tasks. It is not limited to infrastructure provisioning and can also handle configuration management.

    *Example Ansible playbook for installing Nginx on Ubuntu:*
    ```yaml
    ---
    - name: Install Nginx
      hosts: web_servers
      become: true

      tasks:
        - name: Update apt cache
        apt:
            update_cache: yes

        - name: Install Nginx
        apt:
            name: nginx
            state: present
    ```

- **AWS CloudFormation**: CloudFormation is Amazon's IaC service, allowing users to define and provision AWS infrastructure using JSON or YAML templates.

    *Example CloudFormation template for creating an EC2 instance:*
    ```yaml
    Resources:
        MyInstance:
            Type: "AWS::EC2::Instance"
            Properties:
                ImageId: "ami-0c55b159cbfafe1f0"
                InstanceType: "t2.micro"
    ```

#### **Benefits of IaC**
- **Consistency**: IaC ensures that infrastructure environments are consistent across development, testing, and production stages.

- **Scalability**: Automated provisioning allows for scaling infrastructure resources up or down based on demand.

- **Reproducibility**: IaC enables the recreation of entire infrastructure environments reliably, reducing the risk of configuration drift.

- **Collaboration**: Storing IaC scripts in version control facilitates collaboration among team members and provides a history of changes.

- **Auditability**: Infrastructure changes are tracked, allowing for auditing and compliance with organizational policies.

### **Infrastructure Scaling**

#### **Strategies for Infrastructure Scaling**
- **Elasticity**: Cloud environments provide elasticity, allowing resources to automatically scale based on demand.

- **Load Balancing**: Distributing incoming traffic across multiple servers ensures efficient resource utilization and improved fault tolerance.

- **Caching**: Implementing caching mechanisms at various levels can enhance performance and reduce the load on backend systems.

- **Optimizing Resource Allocation**: Regularly assess and optimize resource allocation based on usage patterns and requirements.

- **Decomposition**: Breaking down monolithic architectures into microservices allows for more granular scaling of components.

#### **Horizontal vs. Vertical Scaling**
- **Horizontal Scaling**: Adding more instances of resources (e.g., servers) to distribute the load. It improves redundancy and handles increased demand.

- **Vertical Scaling**: Increasing the capacity of existing resources (e.g., upgrading server hardware). It provides a single, more powerful resource.

#### **Auto-Scaling**
- **Definition**: *Auto-scaling automatically adjusts the number of compute resources based on demand.*

- **Benefits**: *Ensures optimal performance, cost-efficiency, and availability by dynamically scaling resources up or down.*

- **Implementation**: *Cloud providers offer auto-scaling solutions. For example, AWS Auto Scaling allows you to define scaling policies based on metrics like CPU utilization.*

## **DevSecOps in System Design**
*DevSecOps, an evolution of the DevOps culture, integrates security practices into the software development and delivery process. It aims to build security into the development lifecycle from the beginning, rather than treating it as a separate phase. When applied to system design, DevSecOps enhances security by considering it as an integral part of the overall design and development process.*

### **DevSecOps principles in system design**:

- **Threat Modeling**:
    - **Principle**: Identify potential security threats and vulnerabilities at the design stage through threat modeling.
    - **Implementation**: Conduct threat modeling sessions to analyze the system architecture and identify potential security risks. Mitigate these risks by incorporating security controls into the design.

- **Secure Coding Practices**:
    - **Principle**: Promote secure coding practices to prevent common vulnerabilities during the development phase.
    - **Implementation**: Provide training to development teams on secure coding practices, conduct code reviews with a focus on security, and use automated tools to identify and address security issues in the code.

- **Infrastructure as Code (IaC) Security**:
    - **Principle**: Treat infrastructure as code and apply security practices to the code that defines and configures the system infrastructure.
    - **Implementation**: Use IaC tools such as Terraform or Ansible securely. Apply principles like the principle of least privilege to infrastructure configurations.

- **Automated Security Testing**:
    - **Principle**: Integrate automated security testing into the continuous integration/continuous deployment (CI/CD) pipeline.
    - **Implementation**: Include static application security testing (SAST), dynamic application security testing (DAST), and software composition analysis (SCA) tools in the CI/CD process to identify and remediate security vulnerabilities early in the development lifecycle.

- **Container Security**:
    - **Principle**: Address security concerns related to containerized applications.
    - **Implementation**: Secure container images, use container orchestration tools with built-in security features (e.g., Kubernetes), and regularly scan container images for vulnerabilities.

- **Continuous Monitoring**:
    - **Principle**: Implement continuous monitoring to detect and respond to security threats.
    - **Implementation**: Use monitoring tools to collect and analyze security-related metrics and logs. Implement anomaly detection and alerting mechanisms to identify potential security incidents.

- **Access Control and Identity Management**:
    - **Principle**: Enforce strong access controls and identity management practices.
    - **Implementation**: Implement role-based access control (RBAC), enforce the principle of least privilege, and integrate robust identity and authentication mechanisms.

- **Incident Response Planning**:
    - **Principle**: Have an incident response plan in place to handle security incidents effectively.
    - **Implementation**: Develop and regularly test an incident response plan that outlines the steps to be taken in the event of a security incident. Ensure clear communication and coordination among relevant stakeholders.

- **Collaboration and Communication**:
    - **Principle**: Foster collaboration and communication between development, operations, and security teams.
    - **Implementation**: Encourage cross-functional teams, share security knowledge across teams, and use collaboration tools to facilitate communication.

- **Compliance as Code**:
    - **Principle**: Treat compliance requirements as code and automate compliance checks.
    - **Implementation**: Embed compliance checks into the CI/CD pipeline, use tools for automated compliance monitoring, and keep compliance configurations version-controlled.

*Integrating security into system design through DevSecOps practices helps create a more resilient and secure software development lifecycle. By automating security measures and fostering collaboration among teams, organizations can build and deliver systems that are not only functional and efficient but also resilient to security threats.*

### **DevSecOps Best Practices**
#### **Security as Code**
**Definition**: *Security as Code involves integrating security practices into the DevOps pipeline, and treating security configurations and policies as code.*
**Benefits**:

- **Early Detection**: Identifying and addressing security issues early in the development process.

- **Consistent Policies**: Ensuring consistent application of security policies across environments.

**Key Practices**:

- **Static Application Security Testing (SAST)**: Scanning the application's source code for security vulnerabilities.
- **Dynamic Application Security Testing (DAST)**: Assessing the application in its runtime environment for vulnerabilities.

**Continuous Security Monitoring**

- **Real-Time Threat Detection**: Implementing tools and processes for real-time monitoring of security threats and vulnerabilities.

- **Automated Incident Response**: Integrating automated incident response mechanisms to address security incidents promptly.

### **Infrastructure Security**

- **Secure Configuration Management**

    - **Configuration Baselines**: Establishing secure configuration baselines for operating systems, databases, and other infrastructure components.

    - **Automated Configuration Checks**: Implementing automated checks to ensure that configurations adhere to security best practices.

- **Network Security**

    - **Network Segmentation**: Dividing the network into segments to contain and mitigate the impact of security breaches.

    - **Firewalls and Intrusion Detection/Prevention Systems (IDS/IPS)**: Deploying firewalls and IDS/IPS to monitor and control network traffic.

### **Compliance and Governance**

- **Compliance Automation**: Automating compliance checks to ensure that systems adhere to regulatory requirements and internal policies.

- **Audit Trails and Reporting**: Maintaining comprehensive audit trails and generating reports for compliance and governance purposes.

### **Incident Response in DevSecOps**
- **Incident Identification**: Implementing mechanisms for promptly identifying security incidents and anomalies.

- **Response Plans**: Develop and regularly test incident response plans to ensure a swift and coordinated response to security events.

### **DevSecOps Culture**
- **Security Awareness Training**: Ensuring that team members are well-trained on security best practices and are aware of their roles in maintaining security.

- **Cross-Functional Collaboration**: Fostering collaboration between security, development, and operations teams for a holistic approach to security.

### **Case Studies in DevSecOps**
#### **Real-world Examples**
- **Success Stories**: Examining instances where DevSecOps practices have led to improved security postures.

- **Challenges and Lessons Learned**: Analyzing challenges faced and lessons learned in implementing DevSecOps in various organizations.

### **Continuous Monitoring and Improvement**

#### **Security Metrics and KPIs**

- **Selection of Metrics**: Identifying key security metrics and Key Performance Indicators (KPIs) to measure the effectiveness of security controls.

- **Continuous Evaluation**: Regularly evaluating and refining security metrics to align with evolving threats and organizational goals.

#### **Feedback Loops**
- **Feedback Mechanisms**: Establishing feedback loops within the DevSecOps pipeline to provide insights into the impact of security measures.
- **Adaptive Security Measures**: Using feedback to adapt security measures, ensuring they remain effective against emerging threats.

### **Future Trends in DevSecOps**
#### **Artificial Intelligence (AI) and Machine Learning (ML) in Security**
- **Automated Threat Detection**: Leveraging AI and ML for automated detection of security threats.

- **Behavioral Analytics**: Using AI and ML to analyze user and system behavior for anomaly detection.

### **DevSecOps for Cloud-Native Environments**
- **Security in Cloud-Native Architectures**: Addressing specific security considerations in cloud-native application development.

- **Container Security**: Ensuring the security of containerized applications and orchestration platforms.

### **Hands-On Workshop**
#### **Practical Implementation**
- **Security Toolchain Integration**: Integrating security tools into the CI/CD pipeline for automated security checks.

- **Incident Response Simulation**: Conduct a simulated incident response exercise to practice and refine response procedures.

### **Continuous Learning and Community Involvement**
- **Security Training and Certifications**: Encouraging continuous learning through security-related training and certifications.

- **Participation in Security Communities**: Involvement in security communities for knowledge sharing and staying informed about industry best practices.


## **System Design | Practical Approach**

### **Types of Entities**

- **Logical Entity**
    - **Components or Modules**: These are the functional units or building blocks of the system. Each component/module performs a specific set of tasks or functions. For example, in a banking system, you might have components for customer management, account management, and transaction processing.

    - **Data Models**: Logical entities also include the data structures and models used by the system. This involves defining the types of data the system will handle, the relationships between data elements, and the operations that can be performed on the data.

    - **Interfaces**: Logical entities encompass the interactions between various system components. Interfaces define how different modules or components communicate with each other. This can include method calls, message passing, or other communication protocols.

    - **Business Rules**: Logical entities also encapsulate the business rules or logic that govern how the system operates. For instance, in a retail system, there might be business rules for calculating discounts, handling returns, or managing inventory.

- **Tangible Entity**
    - **Hardware Components**: Tangible entities include the physical components of the system, such as servers, storage devices, networking equipment, and other hardware elements.

    - **Software Components**: These are the actual programs or applications that run on the hardware. Tangible software entities include the executable code, libraries, and frameworks that make up the system.

    - **Data Storage**: Tangible entities also involve the physical storage of data. This can include databases, file systems, and other storage mechanisms.

    - **User Interfaces**: Tangible entities encompass the user interfaces through which users interact with the system. This can include graphical user interfaces (GUIs), command-line interfaces, or application programming interfaces (APIs).

### **Client-Server Architecture**

*Client-server architecture is a network architecture in which a client, typically a user's machine, makes requests and a server, which hosts resources, processes these requests. This model is widely used in distributed computing and network-based applications.*

Here are the key components and characteristics of client-server architecture:

#### **Client**:

- **Definition**: *The client is the end-user device or application that requests services or resources from the server.*
- **Functionality**: *Clients send requests to the server for specific tasks or data.*
- **Types**: *Clients can vary in complexity and functionality. Examples include web browsers, mobile apps, desktop applications, and more.*

##### **Thick Client**:
- Also known as "Fat Client" or "Rich Client."
- In a thick client architecture, a significant portion of the application's processing logic and user interface resides on the client side (end-user device).
- The client is responsible for a substantial part of the application's functionality, data processing, and presentation.
- Thick clients often require more resources (memory, processing power) on the user's device.
- Examples of thick clients include traditional desktop applications and some mobile apps that store a significant part of the application logic locally.


##### **Thin Client**:
- In a thin client architecture, the client side is minimized, and most of the application's processing logic and data management occurs on the server.
- The client's primary role is to display the user interface and handle user input. It relies heavily on the server for processing and data storage.
- Thin clients typically require fewer resources on the user's device because much of the application's heavy lifting is done on the server.
- Web browsers are a common example of thin clients, especially in web-based applications where the server handles most of the processing, and the browser renders the user interface.

- **Server**:
    - **Definition**: The server is a dedicated machine or software application that provides services or resources to clients.
    - **Functionality**: Servers process client requests, perform the necessary operations, and send back the results or data.
    - **Types**: Servers can be specialized for specific purposes, such as web servers, database servers, file servers, and application servers.

- **Communication**:
    - **Request-Response Model**: Clients send requests to servers, and servers respond to these requests with the requested data or services.
    - **Protocols**: Communication between clients and servers often relies on standardized protocols like HTTP, HTTPS, FTP, or custom protocols depending on the application.

### **2-Tier Architecture**:
- Also known as "Client-Server" architecture.
- In a 2-tier architecture, the application is divided into two main components: the client (front end) and the server (back end).
- The client is responsible for the user interface and application logic, while the server handles the database and business logic.
- Communication primarily occurs between the client and the server.

### **3-Tier Architecture**:
- In a 3-tier architecture, the application is divided into three main components: the presentation layer (client), the application layer (server), and the data layer (database).
- The presentation layer is responsible for the user interface, the application layer handles business logic, and the data layer manages data storage and retrieval.
- Communication flows between the client, the application server, and the database server.

### **N-Tier Architecture**:
- N-tier architecture is a generalized term that represents any architecture with more than three tiers. It could be 4-tier, 5-tier, and so on, depending on the complexity of the application.
- In an N-tier architecture, additional tiers may be introduced for various purposes, such as security, scalability, or specific functionalities.
- Each tier represents a logical separation of concerns, and communication flows between the tiers based on the specific architecture.

### **Proxies**
*Proxies play a significant role in system design by acting as intermediaries between clients and servers. They are used to improve performance, security, and accessibility in various ways.*

Here are some common use cases of proxies in system design:

#### **Load Balancing**:
- **Description**: Load balancer proxies distribute incoming network traffic across multiple servers to ensure that no single server is overwhelmed.
- **Benefits**: Improved scalability, availability, and reliability by distributing the load efficiently.

#### **Caching Proxies**:
- **Description**: Proxies can cache frequently requested content or data, reducing the need to fetch it from the original server repeatedly.
- **Benefits**: Faster response times, reduced server load, and bandwidth savings, especially for static or infrequently changing content.

#### **Reverse Proxies**:
- **Description**: A reverse proxy sits between client devices and a server, forwarding client requests to the server and returning the server's responses to the clients.
- **Benefits**: Enhances security by hiding the internal structure of the server, load balancing, caching, and providing additional features like SSL termination.

#### **Security Proxies**:
- **Description**: Proxies can be used to inspect and filter network traffic for security purposes, such as firewalls, intrusion detection systems (IDS), or web application firewalls (WAF).
- **Benefits**: Improved security by monitoring and controlling the flow of traffic, protecting against malicious activities.

#### **Content Filtering Proxies**:
- **Description**: Proxies can be employed to filter and control access to content based on predefined policies, such as blocking certain websites or types of content.
- **Benefits**: Enhanced control over the content accessed by users, improved security, and compliance with organizational policies.

#### **Gateway Proxies**:

**Description**: Proxies can serve as gateways between different networks or protocols, translating requests and responses as needed.
**Benefits**: Integration of diverse systems, communication between different network protocols, and improved interoperability.

#### **API Gateways**:
- **Description**: Proxies can act as API gateways, providing a unified entry point for multiple microservices or APIs.
- **Benefits**: Centralized management of APIs, authentication, authorization, logging, and monitoring.

#### **Compression Proxies**:
- **Description**: Proxies can compress outgoing data before sending it to the client, reducing bandwidth usage and improving performance.
- **Benefits**: Faster data transfer, reduced latency, and improved user experience, especially in bandwidth-constrained environments.

#### **Forward Proxies**:
- **Description**: Forward proxies sit between client devices and the internet, forwarding client requests to external servers.
- **Benefits**: Anonymity, content filtering, and caching for client devices accessing external resources.

*The use of proxies in system design provides flexibility, scalability, and improved performance while addressing various system requirements. The specific proxy types employed depend on the goals and constraints of the system being designed.*

### **Database and their types**
*Databases are structured collections of data that are organized in a way that facilitates efficient storage, retrieval, and management of data. There are various types of databases, each designed for specific use cases and requirements.*

Here are some common types of databases:

#### **Relational Databases (RDBMS)**:
- **Description**: Relational databases organize data into tables with rows and columns. They use a schema to define the structure of the data.
- **Key Characteristics**:
    - Tables with relationships between them.
    - SQL (Structured Query Language) for querying and manipulating data.
    - ACID properties (Atomicity, Consistency, Isolation, Durability) to ensure data integrity.
- **Examples**: MySQL, PostgreSQL, Oracle Database, Microsoft SQL Server.


#### **NoSQL Databases**:

- **Description**: NoSQL databases are designed to handle unstructured or semi-structured data. They provide flexible schemas and are suitable for scalable and distributed environments.
- **Key Characteristics**:
    - Dynamic schema.
    - Support for horizontal scaling.
    - Various data models, including document-oriented, key-value, wide-column store, and graph databases.
- **Examples**: MongoDB (document-oriented), Cassandra (wide-column store), Redis (key-value)


## **Kafka**
*Apache Kafka is an open-source distributed streaming platform designed to handle real-time data feeds and event streams. Developed by the Apache Software Foundation, Kafka is widely used for building scalable and fault-tolerant systems for data streaming and event-driven architectures.*

Here are key aspects of Kafka:

- **Publish-Subscribe Model**: *Kafka follows a publish-subscribe messaging paradigm. Producers publish messages to topics, and consumers subscribe to these topics to receive the messages.*

- **Topics**: *Topics in Kafka represent categories or feeds to which messages are published. Producers publish messages to topics, and consumers subscribe to topics to consume the messages.*

- **Partitions**: *Each topic is divided into partitions, which allow for parallelism and scalability. Partitions enable multiple consumers to process messages concurrently.*

- **Brokers**: *Kafka operates as a distributed system with multiple servers called brokers. Each broker is responsible for managing partitions, storing data, and serving clients.*

- **Producers**: *Producers are applications or systems that publish messages to Kafka topics. They send data to specific topics, and Kafka ensures that the data is distributed across partitions.*

- **Consumers**: *Consumers are applications or systems that subscribe to topics and process the messages. Consumers can be part of a consumer group, allowing for parallel processing and load balancing.*

- **Consumer Groups**: *Consumer groups enable parallel processing of messages by allowing multiple consumers to work together. Each partition is consumed by only one consumer within a consumer group, ensuring that all messages in a partition are processed in order.*

- **Replication**: *Kafka supports data replication for fault tolerance. Each partition can have multiple replicas distributed across different brokers. If a broker fails, another replica can take over to ensure data availability.*

- **Retention**: *Kafka retains messages for a configurable period. This allows consumers to catch up on messages even if they are offline for a certain period.*

- **Log-Structured Storage**: *Kafka stores messages in a log-structured format on disk. This design provides efficient and sequential read and write access to messages.*

- **Scalability**: *Kafka is designed for horizontal scalability. Additional brokers can be added to a Kafka cluster to handle increased data throughput.*

- **Use Cases**: *Kafka is used in various scenarios, including real-time event streaming, log aggregation, monitoring, data integration, and building event-driven architectures.*

- **Ecosystem**: *Kafka has a rich ecosystem of connectors, tools, and integrations. Kafka Connect provides a framework for connecting Kafka to various data sources and sinks, and Kafka Streams allows for stream processing within the Kafka ecosystem.*

*Apache Kafka has become a fundamental component in many modern data architectures, providing a robust and scalable foundation for building real-time, event-driven systems. It is particularly well-suited for scenarios where high throughput, fault tolerance, and scalability are critical requirements.*

## **Entity-Relationship (ER) Diagram**
*An Entity-Relationship (ER) diagram is a visual representation of the entities (objects or concepts) within a system and the relationships between those entities. ER diagrams are commonly used in database design to model the structure of a database and illustrate how data entities relate to each other.*

Here are some key components of an ER diagram:

- **Entities**: *Entities represent real-world objects or concepts about which data will be stored in the database. Examples of entities include "Customer," "Product," or "Employee."*

- **Attributes**: *Attributes are the properties or characteristics of entities. For example, a "Customer" entity might have attributes such as "CustomerID," "Name," and "Email."*

- **Relationships**: *Relationships define how entities are related to each other. They establish connections between entities and describe the nature of the association. Relationships can be one-to-one, one-to-many, or many-to-many.*

- **Cardinality**: *Cardinality specifies the number of instances of one entity that can be related to the number of instances of another entity. It is expressed using notations like "1" (one), "M" (many), or "0..1" (zero or one).*

- **Primary Key**: *A primary key uniquely identifies each record in an entity. It is typically represented by an underlined attribute in an ER diagram.*


- **Foreign Key**:* A foreign key is a field that refers to the primary key in another table. It establishes a link between two tables and is represented in an ER diagram to show relationships.*

Here is a simplified example of an ER diagram for a university database:

```txt
+----------------+         +-------------------+
|   Student      |         |      Course       |
+----------------+         +-------------------+
| StudentID (PK) |---------| CourseID (PK)     |
| Name           |         | Title             |
| Major          |         | Credits           |
+----------------+         +-------------------+
         |
         | Enrolls
         |
+--------------------------+
|        Enrollment       |
+--------------------------+
| EnrollmentID (PK)       |
| StudentID (FK)          |
| CourseID (FK)           |
| Grade                   |
+--------------------------+

```

In this example:

- "Student" and "Course" are entities.
- "Enrollment" represents the relationship between students and courses.
- "StudentID" and "CourseID" are primary keys, and "EnrollmentID" is a primary key for the "Enrollment" entity.
- The "Enrollment" entity includes foreign keys ("StudentID" and "CourseID") that reference the primary keys in the "Student" and "Course" entities, establishing the relationships.

*ER diagrams serve as valuable tools for database designers and developers to understand the structure of a database and ensure that the relationships and constraints between entities are well-defined.*

## RDBMS vs NoSQL Database Comparison

### RDBMS (Relational Database Management Systems)

#### Definition:
RDBMS is a type of database management system that uses a tabular structure with rows and columns to store and manage data.

#### Data Model:
- Follows a structured and predefined schema.
- Data is organized in tables with fixed columns.

#### Schema:
- Requires a predefined schema.
- Enforces data integrity through relationships and constraints.

#### Scalability:
- Vertical scaling is common, adding more resources to a single server.
- May face challenges with horizontal scaling.

#### Transactions:
- ACID (Atomicity, Consistency, Isolation, Durability) properties are enforced.
- Well-suited for applications where data integrity is critical.

#### Use Cases:
- Well-suited for complex queries and transactions.
- Commonly used in traditional business applications, finance, and applications with complex relationships.

### NoSQL Databases

#### Definition:
NoSQL databases are a type of database management system that provides a flexible schema and is designed for handling unstructured or semi-structured data.

#### Data Model:
- Follows various data models, including document-oriented, key-value pairs, wide-column stores, and graphs.
- No strict schema requirements.

#### Schema:
- Schema-less or dynamic schema.
- Allows flexibility to add or remove fields without affecting existing data.

#### Scalability:
- Well-suited for horizontal scaling across distributed systems.
- Can easily scale out to handle large volumes of data.

#### Transactions:
- May not strictly adhere to ACID properties.
- Provides eventual consistency, making it suitable for distributed and highly scalable systems.

#### Use Cases:
- Ideal for scenarios with rapidly changing or evolving data structures.
- Commonly used in web applications, real-time big data analytics, and applications with high scalability requirements.

### Conclusion:

| Criteria                | RDBMS                            | NoSQL Database                    |
|-------------------------|----------------------------------|-----------------------------------|
| Data Model              | Tabular structure with fixed schema | Flexible data models              |
| Schema                  | Predefined schema                 | Dynamic or schema-less            |
| Scalability            | Commonly scales up; can scale out with replicas, partitioning, or distributed SQL | Commonly designed for horizontal partitioning |
| Transactions           | Strong multi-row ACID transactions are typical | Guarantees vary; many products support ACID transactions with different scope and cost |
| Use Cases               | Complex queries and transactions  | Rapidly changing data structures  |

In conclusion, choose a database from access patterns, consistency and transaction
requirements, data shape, scale, operational maturity, and cost. "SQL versus
NoSQL" is not a simple choice between consistency and scalability; modern systems
overlap substantially, so verify the guarantees of the specific product.

## System Design Practice

## Database Design Tips

### Factors for DB Design

#### Structured vs Un-structured

#### Query Pattern

#### Scaling


### Other Data storages
#### Caching Solution
- Redis


#### File Storage

##### Blob Storage 
- Amazon S3

#### Content Delivery Network (CDN)

#### Searching Solution (Text Searching Engine)
- Elastic Search
- Solr

#### Time series Data, metric system
- InfluxDB
- Open TSDB

#### Data storage for analytics
- Dataware house
- Hadoop

### How to choose DB
- Structured, Need ACID
    - RDBMS
        - MySQL
        - Oracle
- Unstructured
    - Document DB
        - Mongo
        - couch base
- Ever Increasing, *i.e. ride data for Uber* 
    - Columnar DB
        - Cassandra
        - HBase


### Tips
- Use of the combination of DBs
- Complete data in RDB, small info in Document Based




## **Interview Prep**













### Caching Solution:
- Redis

### File storage | Image/Video
- Blob Storage | amazon s3
- Content Delivery Network (CDN): Distribute the stored blob based on geographical location

### Text Search Engine | product, movie, location search
- Elastic Search | Solr
- fuzzy search | wrong spelling of the searched word
- maybe data loss

### Metric tracking system 
- no random data accessed
- time-series | open time series database Open TSDB

### analytics | data dump
- Dataware House | Hadoop

### Selecting RDBMS 
- Structured Data
    - Yes 
        - Need ACID
            - Atomicity
            - Consistency
            - Isolation
            - Durability
        - MySQL, Oracle, SQL Server, Postgres
    - No
        - Document Based DB | Catalogue
            - MongoDB, Couch Base
        - Ever Increasing Data
            - Uber | continues data update
            - Columnar DB
            - Cassandra, HBase

### System Design

- Requirement Analysis
    - Functional Requirements
    - Non-Functional Requirements
- Stakeholders
    - users
- Potential Issues
- Designing | Discussion | assumptions
    - FR1
    - FR2
    - FR3
- Infrastructure Discussion
    - NFR1
    - NFR2
    - NFR3
- Flow Diagram

#### Google Map System Design

- Requirement Analysis
    - Functional Requirements
        - Identify Roads, Routes
            - Use Government Sources
            - Use the user's travel data, to identify the roads/routes
        - Distance, ETA b/w 2 Points
        - Pluggable inputs for traffic, construction, weather, and closures
    - Non-Functional Requirements
        - High Availability
        - Good Accuracy
        - Not too slow
        - Scale to a global user base and large road graph
- Stakeholders
    - Users
- Potential Issues
    - No proper location for this huge amount of data about the road/routes
    - Multiple reasons that can change ETA b/w 2 points

- Designing | Discussion | assumptions
    - FR: Finding Shortest Route
        - Divide the whole area into smaller sections 1Km*1Km, segment
        - Each segment will store the exit point for that segment
        - use X, and Y coordinates to find the location of the current user
        - Every road has a weight | time to cross the road
        - Directed Graph, (length, time taken)
        - Use a hierarchical road graph to avoid searching the entire world graph
        - Use Dijkstra's algorithm or A* with an admissible heuristic; precompute
          frequently used routes where it is cost-effective
        - Cache route results briefly and invalidate or re-rank them when traffic,
          incidents, or closures materially change edge costs
        - Recompute from the user's current position when they leave the selected route
    - FR: Distance, ETA b/w 2 Points
        - Edges, and weights
            - Distance
            - ETA
            - Avg. Speed
    - FR: Plugable | Easily addition of traffic, construction, etc.
        - Traffic, weather, all these will not be part of edge, weight
        - These will be the factors that will change
            - avg. speed
        - Traffic
            - low
            - medium
            - high
            - going from low to medium, the average speed was reduced by 20%
        - Weather
            - good
            - bad
            - going from good to bad, the average speed was reduced by 60%
        - Use historical data for ETA, Sunday ETA
        - traffic detection, average speed reduces by more than 60%
- Infrastructure Discussion
    - Replicate stateless routing services across failure zones behind load balancers
    - Partition the road graph geographically and keep nearby partitions in memory
    - Stream location and incident updates through a durable event log
    - Track route latency, ETA error, map freshness, and unavailable road segments


- Flow diagram

![Google Maps system design flow](flowdiagrams/GoogleMapSystemDesignFlow.png)




#### E-Commerce Platform System Design

- Stakeholders
    - User
    - Admin
- Requirement Analysis
    - Functional Requirements
        - User
            - should be able to sign up and sign in
                - CRUD APIs
                - SQL DB
            - should be able to view the list of products and product
                - CRUD APIs
                - NoSQL DB
            - should be able to manage cart
                - CRUD APIs
                - SQL DB
            - should be able to add address and contact details
                - CRUD APIs
                - NoSQL DB
            - should be able to see the available payment options
                - CRUD APIs
                - SQL DB
            - should be able to checkout using selected payment mode
                - External APIs to manage payment
                - SQL DB to manage payment data
            - should be able to manage the placed order
                - CRUD APIs
                - SQL DB
        - Admin
            - should be able to manage products
                - CRUD APIs
                - NoSQL DB
            - should be able to change different configuration
                - CRUD APIs for configurations
                - SQL/NoSQL DBs
            - should be able to change the payment option
                - CRUD APIs
                - SQL DB
            - should be able to view/manage user
                - CRUD APIs
                - SQL DB
    - Non-Functional Requirements
        - Data security
            - Use encryption in transit and at rest; hash passwords with a
              password-specific algorithm
        - Not very slow
            - Use caching and indexing based on measured access patterns
        - Accuracy
            - Use validation APIs
- Potential Issues
    - Duplicate payment callbacks and order retries require idempotency keys
    - Inventory can change during checkout; reservations need expiration and reconciliation
    - Search/catalog data can lag behind the transactional source of truth
    - Hot products and promotions can overload inventory, cart, or checkout partitions


![E-Commerce%20Platform.png](flowdiagrams/E-Commerce%20Platform.png)



#### Video Streaming Platform

- Functional requirements
    - Creators upload videos and track processing status
    - Viewers browse, search, and play videos on common devices
    - The platform records watch progress and engagement events
- Non-functional requirements
    - Playback starts quickly and adapts to changing network conditions
    - Uploaded media is durable; playback remains highly available
    - Metadata and search may be eventually consistent, but access control must
      take effect promptly

##### Core flow

1. The upload service authenticates the creator, creates a video record, and
   returns a short-lived multipart object-storage upload URL.
2. Completing the upload emits an event. Workers scan the source, transcode it
   into multiple resolutions and bitrates, create HLS/DASH manifests and
   thumbnails, and update processing status.
3. The metadata service publishes the processed video and asynchronously updates
   the search index and recommendation features.
4. A playback request checks visibility and entitlement, then returns a signed
   manifest URL. The player fetches media segments from the nearest CDN edge and
   switches bitrate using observed bandwidth and buffer health.
5. Clients batch watch events into a durable stream. Independent consumers update
   analytics, progress, counters, and recommendation inputs.

##### Storage and scaling

- Store original and transcoded media in replicated object storage; keep metadata,
  ownership, and visibility in a transactional database.
- Put immutable media segments behind a CDN with versioned keys and long cache
  lifetimes. Cache mutable metadata separately with short TTLs or invalidation.
- Partition metadata by video ID and event streams by video or user when ordering
  within that key matters. Salt or aggregate counters for viral-video hot keys.
- Make upload completion and transcoding idempotent. Use retries with backoff, a
  dead-letter path, and a reconciliation job for stuck workflows.
- Apply quotas, rate limits, content validation, signed URLs, and authorization at
  both metadata and media-delivery boundaries.

##### Operability and trade-offs

- Monitor upload success, transcode queue age, processing time, playback-start
  latency, rebuffer ratio, CDN hit rate, error rate, and cost per streamed minute.
- Multi-region metadata writes improve failover but increase consistency and
  conflict complexity. A simpler first version can use one write region with
  replicated reads while the CDN serves media globally.
- Pre-transcoding every format reduces playback delay but increases storage and
  compute cost. Generate the most common renditions first and add rare formats on
  demand when product requirements allow it.
