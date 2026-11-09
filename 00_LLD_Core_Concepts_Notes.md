# Low Level Design (LLD) - In-Depth Guide

Low Level Design (LLD) is a component-level design process that follows High Level Design (HLD). While HLD focuses on system architecture, databases, and microservices (the "macro" view), LLD dives deep into the "micro" view. It involves designing the actual classes, interfaces, relationships, and data structures that will make up each component.

## 1. Core Principles of LLD

The foundation of good LLD rests on Object-Oriented Programming (OOP) concepts and the SOLID principles.

### Object-Oriented Programming (OOP) Concepts
- **Encapsulation**: Bundling data (attributes) and methods (behavior) that operate on the data into a single unit (class). It also involves restricting direct access to some of the object's components (using access modifiers like `private`, `protected`).
- **Abstraction**: Hiding complex implementation details and showing only the essential features of an object. This reduces complexity and allows the programmer to focus on interactions.
- **Inheritance**: A mechanism where a new class derives properties and behaviors from an existing class. It promotes code reusability and establishes an "is-a" relationship.
- **Polymorphism**: The ability of different classes to respond to the same method call in their own specific way. This is typically achieved through method overriding (runtime) or method overloading (compile-time).

### SOLID Principles
SOLID is an acronym for five design principles intended to make software designs more understandable, flexible, and maintainable.

1. **S - Single Responsibility Principle (SRP)**
   - *A class should have one, and only one, reason to change.*
   - **Meaning**: Every class or module should focus on a single task or responsibility. If a class handles user authentication, it shouldn't also handle database logging.

2. **O - Open/Closed Principle (OCP)**
   - *Software entities (classes, modules, functions, etc.) should be open for extension, but closed for modification.*
   - **Meaning**: You should be able to add new functionality without changing existing code. This is usually achieved using interfaces or abstract classes.

3. **L - Liskov Substitution Principle (LSP)**
   - *Objects in a program should be replaceable with instances of their subtypes without altering the correctness of that program.*
   - **Meaning**: A derived class must be substitutable for its base class. If `Bird` has a method `fly()`, and `Penguin` inherits from `Bird`, `Penguin` shouldn't crash when `fly()` is called. If it does, `Penguin` shouldn't inherit from `Bird`.

4. **I - Interface Segregation Principle (ISP)**
   - *Many client-specific interfaces are better than one general-purpose interface.*
   - **Meaning**: Don't force a class to implement interfaces it doesn't use. Instead of one fat interface, break it down into smaller, more specific ones.

5. **D - Dependency Inversion Principle (DIP)**
   - *High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details. Details should depend on abstractions.*
   - **Meaning**: Code should depend on interfaces or abstract classes rather than concrete classes. This reduces coupling and makes the system easier to test and modify.

## 2. The Role of Design Patterns

Design patterns are typical solutions to commonly occurring problems in software design. They are like pre-made blueprints that you can customize to solve a recurring design problem in your code.

Patterns are categorized into three main types:
1. **Creational Patterns**: Deal with object creation mechanisms, trying to create objects in a manner suitable to the situation. (e.g., Singleton, Factory, Builder).
2. **Structural Patterns**: Deal with object composition or identifying a simple way to realize relationships between entities. (e.g., Adapter, Decorator, Facade).
3. **Behavioral Patterns**: Deal with communication between objects, defining how they interact and fulfill a given task. (e.g., Strategy, Observer, Command).

## 3. How to Approach an LLD Problem (e.g., in an Interview)

When tasked with designing a system at a low level (e.g., "Design a Parking Lot", "Design BookMyShow", "Design an Elevator System"), follow these steps:

1. **Requirements Clarification**: Ask questions to narrow down the scope. What features are strictly required? What are the constraints?
2. **Identify Entities (Classes)**: Find the core nouns in the problem statement. For a parking lot: `Vehicle`, `Ticket`, `ParkingSpot`, `EntryGate`, `ExitGate`.
3. **Define Attributes and Methods**: What does each entity know (attributes) and what can it do (methods)?
4. **Establish Relationships**: How do the entities interact?
   - *Association*: General relationship (e.g., Driver uses a Car).
   - *Aggregation*: "Has-a" relationship where the child can exist independently of the parent (e.g., Department has Teachers).
   - *Composition*: "Has-a" relationship where the child's lifespan depends on the parent (e.g., House has Rooms).
5. **Apply Design Patterns**: Look for common problems and apply patterns. For example, if you need a single configuration manager, use a Singleton. If the pricing strategy for a parking lot changes based on time or vehicle type, use a Strategy pattern.
6. **Code Structure**: Write the interfaces and class definitions (often in a language like Java, C++, or TypeScript) to demonstrate the architecture.

(Explore the other files in the `lld/` folder for deep dives into individual design patterns!)
