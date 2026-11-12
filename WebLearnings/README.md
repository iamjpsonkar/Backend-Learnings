> # HTML : Hyper Text Markup Language

## Basic Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Title</title>
</head>
<body>
  Content
</body>
</html>
```

## Headings

<h1>H1 Heading</h1>
<h2>H2 Heading</h2>
<h3>H3 Heading</h3>
<h4>H4 Heading</h4>
<h5>H5 Heading</h5>
<h6>H6 Heading</h6>

## Paragraph

<p>P Paragraph</p>

## List

### Ordered List
<ol>
  <li> OL > LI > 1. </li>
  <li> OL > LI > 2. </li>
</ol>

### Unordered List
<ul>
  <li> UL > LI > ● </li>
  <li> UL > LI > ● </li>
</ul>

## Span
<span>This is a SPAN</span>

## NAV
<nav>This is a NAV</nav>

## Header
<header> This is an HEADER</header>

## Article
<article> This is an ARTICLE</article>

## Div
<div>This is a DIV</div>

## Image
<img src="#" alt="This is an IMAGE" />

## LINK
<a href="#"> This is an A</a>

> # CSS : Cascading Style Sheet

## CSS Rule Structure
```
CSS Rule -->
selector {
  Property : Value; <-- Declaration/style
}
```
```css
h1{
  color : blue;
  text-align : center;
  font-size : 20px;
}
```

## Types of CSS

### Inline CSS
Rules are declared inside the Tag
```html
<h1 style="color:blue;">Blue H1 Using Inline CSS</h1>
```

### Internal CSS
Rules are declared inside the style element of the head
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Title</title>
  <style>
    h1{
      color: blue;
    }
  </style>
</head>
<body>
  <h1>Blue H1 Using Internal CSS</h1>
</body>
</html>
```

### External CSS
Rules are declared in an external sylesheet_name.css and then included in an Html file using the link element
Below is the stylesheet.css
```css
h1 {
  color:blue;
}
```
Below is the index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Title</title>
  <link href="./stylesheet.css" type="text/css" rel="stylesheet"/>
</head>
<body>
  <h1>Blue H1 Using External CSS</h1>
</body>
</html>
```

## Common CSS Rules

- color: set the color of the text to the specified value
  ```css
  p {
    color:blue;
  }
  ```

 - font-size: set the size of the text to the specified value
    ```css
    p {
      font-size:2opx;
    }
    ```

- font-family: set the font of the text to the specified value
  ```css
  p {
    font-family:sans-serif;
  }
  ```

- text-transform: transform the text using the specified value
  ```css
  p {
    text-transform:uppercase;
  }
  ```

- font-style: set the style of the text to the specified value
  ```css
  p {
    font-style:italic;
  }
  ```

- line-height: set the spaces between the lines of text to the specified value multiplied by the font size
  ```css
  p {
    line-height:1.5;
  }
  ```

- text-align: set the alignment of the text by the specified value inside the element
  ```css
  p {
    text-align:center;
  }
  ```

- background-color: set the background color of the text by the specified value
  ```css
  p {
    background-color:#f7f7f7;
  }
  ```

- border: set the border property of the text by the specified values
  ```css
  p {
    border:1px solid black;
    /* border: border-size border-type border-color;*/
    /* border-top, border-bottom, border-left, border-right */
  }
  ```

- text-decoration: set the decoration of the text by the specified values
  ```css
  p {
    text-decoration:underline dotted orangered;
    /* text-decoration: text-decoration-line text-decoration-style text-decoration-color*/
  }
  ```

## Combining Selectors
We can specify multiple selectors comma-separated for the common CSS rules
```css
h1, h2, h3 {
  font-family;sans-serif;
}
```

We can also specify rules for a descendent selector using space-separated elements
```css
div p {
  font-size:20px;
}
```

## CSS Selectors

### ID CSS Selector
We can specify rules for an element of Html having an id attribute using ID Selector. There can be only one ID selector inside one Element.
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Title</title>
  <style>
    #head1 {
      color: blue;
    }
  </style>
</head>
<body>
  <h1 id="head1" >Blue H1 Using Internal CSS</h1>
</body>
</html>
```

### Class CSS Selector
We can specify rules for related elements of the HTML having a class attribute using the class Selector. There can be multiple space-separated Classes inside one Element.
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Title</title>
  <style>
    .head2 {
      color: blue;
    }
  </style>
</head>
<body>
  <h1 class="head2" >Blue H1 Using Internal CSS</h1>
  <h2 class="head2" >Blue H1 Using Internal CSS</h2>
  <h3 class="head2" >Blue H1 Using Internal CSS</h3>
</body>
</html>
```

### Element Selector
```css
p {
  color:black;
}
```

### Important selector
```css
p {
  color:#000000 !important;
}
```

## Working with Colors

### The RGB Model
Every color can be represented using a combination of Red, Green and Blue

- RGB notation:
  Red, Green, Blue = [0, 255], [0, 255], [0, 255]
  ```css
  /* red color*/
  p{
    color:rgb(255, 0, 0);
  }
  ```

- RGBA notation: 
  We can specify an alpha/transparency value for colors using RGBA
  Red, Green, Blue, Alpha = [0, 255], [0, 255], [0, 255], [0.0, 1.0]
  ```css
  /* red color*/
  p{
    color:rgba(255, 0, 0, 0, 1);
  }
  ```

- Hexadecimal notation:
  Red, Green, Blue = [00, ff], [00, ff], [00, ff]
  ```css
  /* red color*/
  p{
    color:#ff0000;
  }
  ```

**If all the values specified for RGB are the same we get a gray color from white to black**


## Pseudo Classes

### Selector:first-child
This selects all the first children of type Selector.

```html
<style>
  li:first-child {
    font-weight:bold;
  }
</style>
<ul>
  <li>One</li>
  <li>Two</li>
  <li>Three</li>
</ul>
<br/>
<ol>
  <li>First</li>
  <li>Second</li>
  <li>Third</li>
</ol>
```

Output will be
> - **One**
> - Two
> - Three
> 
> 1. **First**
> 2. Second
> 3. Third

### Selector:last-child
This selects all the last children of type Selector.

```html
<style>
  li:last-child {
    font-weight:bold;
  }
</style>
<ul>
  <li>One</li>
  <li>Two</li>
  <li>Three</li>
</ul>
<br/>
<ol>
  <li>First</li>
  <li>Second</li>
  <li>Third</li>
</ol>
```

Output will be
> - One
> - Two
> - **Three**
> 
> 1. First
> 2. Second
> 3. **Third**

### Selector:nth-child(n)
This selects all the nth children of type Selector. n can be a number. n can be odd/even.

```html
<style>
  li:nth-child(2) {
    font-weight:bold;
  }
</style>
<ul>
  <li>One</li>
  <li>Two</li>
  <li>Three</li>
</ul>
<br/>
<ol>
  <li>First</li>
  <li>Second</li>
  <li>Third</li>
</ol>
```

Output will be
> - One
> - **Two**
> - Three
> 
> 1. First
> 2. **Second**
> 3. Third

**In pseudo-classes, order matters, so it should be a direct child.**

### Selector: link
This will be applied to all the anchor elements having the HREF attribute.
```css
a:link{
  color:#1098ad;
  text-decoration:none;
}
```

### Selector: visited
This will be applied to all the anchor elements which are already visited.
```css
a:link{
  color: #aa2222;
}
```

### Selector: hover
This will be applied to all the anchor elements when the mouse pointer hovers them.
```css
a:hover{
  color: #aa2222;
  font-weight:bold;
  text-decoration:underline dotted #aa2222;
}
```

### a: active
This will be applied to all the anchor elements when the mouse pointer clicks them.
```css
Selector:hover{
  backgroud-color: #000000;
  font-style:italic;
}
```

## Conflicts between Selectors
When there are multiple selectors which are conflicting, then the order of priorities is as follows
1. Declaration marked (!important)
2. Inline style attribute in HTML
3. ID (#) Selector
4. Class (.) or Pseudo-class (:) Selector
5. Element (p, div, h1) Selector
6. Universal (*) Selector

**If conflicting rules are Internal and External then Preference will be given to the last saved one.**

**If conflicting rules are having the same hierarchy then Preference will be given to the last one.**

## Inheritance and the Universal Selector
CSS text properties are inherited from the parent to all the child elements. 


### Universal Selector
It is used to apply the CSS rule to everything.
```css
* {
  color:black;
}
```

## CSS Box Model
It is a rectangular box that has the following things

1. Content: Text, Images
2. Border: A outline around the Content
3. Padding: space between the content and the border
4. Margin: Outer space around the Border

Final width = left border + left padding + element width + right padding + right border

Final height = top border + top padding + element height + bottom padding + bottom border

## Margins and Paddings

### Padding
```css
div {
  padding: 10px;
  /* padding:top=10 right=10 bottom=10 left=10; */

  padding: 10px 20px;
  /* padding:top=10 right=20 bottom=10 left=20; */

  padding: 10px 20px 30px 40px;
  /* padding:top=10 right=20 bottom=30 left=40; */

  padding-top:10px;

  padding-left:10px;

  padding-right:10px;

  padding-bottom:10px;

}
```

### Margin
```css
div {
  margin: 10px;
  /* margin:top=10 right=10 bottom=10 left=10; */

  margin: 10px 20px;
  /* margin:top=10 right=20 bottom=10 left=20; */

  margin: 10px 20px 30px 40px;
  /* margin:top=10 right=20 bottom=30 left=40; */

  margin-top:10px;

  margin-left:10px;

  margin-right:10px;

  margin-bottom:10px;

}
```

**Collapsing margin, In the case of two adjacent elements, only a margin having a higher value is visible.**

## Adding Dimensions
```css
div{
  height:20px;
  width:20px;

  height:100%;
  width:50%;

  height:20px;
  width:auto;

  width:20px;
  height:auto;
}
```

## Centering

Trick to center
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Title</title>
  <style>
    .container{
      width:700px;
      margin-left:auto;
      margin-right:auto;
    }
  </style>
</head>
<body>
  
  <div class="container" style="border:1px solid black;">
    <p style="border:1px solid red;">A certified authorization professional (CAP) is a vendor-neutral certification that tests, validates and certifies an individual’s ability to understand, implement and maintain secure authorization for information systems.</p>
  </div>
</body>
</html>
```

## Types of CSS Box

### Block Level Box
1. Elements are formatted visually as a block.
2. Elements occupy 100% of the width of the parent, no matter what content they have.
3. Elements are stacked vertically by default, one after another.
4. They have line breaks after them.

Examples
```html
<body></body>
<header></header>
<main></main>
<footer></footer>
<section></section>
<nav></nav>
<aside></aside>
<div></div>
<h1></h1>
.
.
.
<h6></h6>
<p></p>
<ul></ul>
<ol></ol>
<li></li>
```
with CSS
```css
class{
  display:block;
}
```

### Inline CSS Box
1. Occupy only the space necessary for its content.
2. causes no line breaks.
3. heights and widths do not apply.
4. padding and margin are applied only horizontally.


Examples
```html
<a href="#"></a>
<img src="" alt=""/>
<strong></strong>
<em></em>
<button></button>
```
with CSS
```css
class{
  display:inline;
}
```

### Inline Block CSS Box
Combination of Inline and Block

1. Block from the inside, inline from outside
2. Occupy only content space
3. Causes no line breaks


Examples with CSS
```css
class{
  display:inline-block;
}
```

## Positioning

### Normal Flow
1. Default positioning
2. Elements "in the flow"
3. Elements are simply laid out according to their order in HTML code
```css
name{
  position:relative;
}
```

### Absolute Positioning
1. Elements are removed from the normal flow: "out of flow"
2. No impact on surrounding elements might overlap them.
3. We use the top, bottom, left or right to offset the element from its relatively positioned container.

**make parent relative, for absolute positioning**

```css
name{
  position:absolute;
  top: 0;
  bottom : 0;
  right: 0;
  left: 0;
}
```

## Pseudo Elements

### first-letter
```css
h1::first-letter{
  font-style:normal;
}
```

### first-line
```css
h1::first-line{
  font-style:normal;
}
```

### after
```css
h1::after{
  content="";
  ...;
}
```

### before
```css
h1::before{
  content="";
  ...;
}
```
> # JS : Javascript

## How to include in HTML
```js
<script src="file.js"></script>
```

## console.log
```js
console.log("Hello");
```

## Let, Const, Var
```js
let a; // best practice
var b; // gloabal scope
const c=10; // can't be changed
```

## Types of datatype
- string
- number
- boolean

## Operators
- `+` concat or addition
- other operators

## Arrays
Arrays in JavaScript are used to store multiple values in a single variable. They are a special type of object, with a numeric index that starts at zero.

### Array Declaration:
You can declare an array using square brackets `[]` and provide values separated by commas:
```js
let fruits = ["Apple", "Banana", "Orange"];
```

### Accessing Array Elements:
You can access elements of an array using square bracket notation with the index:
```js
console.log(fruits[0]); // Output: Apple
console.log(fruits[1]); // Output: Banana
```

### Modifying Array Elements:
You can modify array elements by assigning new values to specific indices:
```js
fruits[0] = "Mango";
console.log(fruits); // Output: ["Mango", "Banana", "Orange"]
```

### Array Length:
You can get the length of an array using the `length` property:
```js
console.log(fruits.length); // Output: 3
```

### Adding Elements:
You can add elements to the end of an array using the `push()` method, or at the beginning using the `unshift()` method:
```js
fruits.push("Grapes");
console.log(fruits); // Output: ["Mango", "Banana", "Orange", "Grapes"]

fruits.unshift("Pineapple", "Grapes");
console.log(fruits); // Output: ["Pineapple", "Mango", "Banana", "Orange", "Grapes"]
```

### Removing Elements:
You can remove elements from the end of an array using the `pop()` method, or from the beginning using the `shift()` method:
```js
fruits.pop();
console.log(fruits); // Output: ["Pineapple", "Mango", "Banana", "Orange"]

fruits.shift();
console.log(fruits); // Output: ["Mango", "Banana", "Orange"]
```

### Array Methods:
JavaScript arrays come with built-in methods for various operations such as `concat()`, `slice()`, `splice()`, `indexOf()`, `includes()`, `join()`, `reverse()`, `sort()`, etc.

```js
var numbers = [3, 1, 2];
var fruits = ["Banana", "Orange", "Apple"];

// concat(): Concatenates two or more arrays
var combinedArray = numbers.concat(fruits);
console.log("concat():", combinedArray);

// slice(): Returns a shallow copy of a portion of an array into a new array
var slicedArray = combinedArray.slice(2, 5);
console.log("slice():", slicedArray);

// splice(): Changes the contents of an array by removing or replacing existing elements and/or adding new elements
var splicedArray = combinedArray.splice(2, 2, "Pineapple", "Grapes");
console.log("splice():", splicedArray, combinedArray);

// indexOf(): Returns the first index at which a given element can be found in the array, or -1 if it is not present
var index = combinedArray.indexOf("Apple");
console.log("indexOf():", index);

// includes(): Determines whether an array includes a certain value among its entries
var includes = combinedArray.includes("Mango");
console.log("includes():", includes);

// join(): Joins all elements of an array into a string
var joinedString = combinedArray.join(" | ");
console.log("join():", joinedString);

// reverse(): Reverses the order of the elements in an array
var reversedArray = combinedArray.reverse();
console.log("reverse():", reversedArray);

// sort(): Sorts the elements of an array in place and returns the sorted array
var sortedArray = numbers.sort();
console.log("sort():", sortedArray);
```


## Objects
objects are a fundamental data type that allows you to store collections of key-value pairs. Objects are versatile and can represent complex data structures.

### Object Declaration
You can declare an object using curly braces `{}` and define its properties inside:
```js
var person = {
  name: "John",
  age: 30,
  city: "New York"
};
```

### Accessing Properties
You can access object properties using dot notation or square bracket notation:
```js
console.log(person.name); // Output: John
console.log(person['age']); // Output: 30
```

### Adding or Modifying Properties:
You can add new properties or modify existing ones by assignment:
```js
person.gender = "Male"; // Adding a new property
person.age = 31; // Modifying an existing property
```

### Deleting Properties:
You can delete properties using the `delete` keyword:
```js
delete person.city;
```

### Object Methods:
You can define functions as properties of an object, which are called methods:
```js
var person = {
  name: "John",
  greet: function() {
      console.log("Hello, my name is " + this.name);
  }
};
person.greet(); // Output: Hello, my name is John
```

### Object keys and Values:
You can get object's properties using  `Object.keys()`, `Object.values()`, or `Object.entries()` methods:
```js
let keys = person.keys();
let values = person.values();
let entities = person.entities();
```
### Object Prototypes:
In JavaScript, objects can inherit properties and methods from other objects through prototypes.
```js
function Person(name, age) {
    this.name = name;
    this.age = age;
}

Person.prototype.greet = function() {
    console.log("Hello, my name is " + this.name);
};

var john = new Person("John", 30);
john.greet(); // Output: Hello, my name is John
```

## Conditional Statements

### If Else
```js
let age = 18;
if(age<18){
  console.log("Not Eligible");
} else {
  console.log("Eligible");
}
```

### Switch
```js
let ch = 2;
switch(ch){
  case 1:
    console.log("I am 1");
    break;
  case 2:
    console.log("I am 2");
    break;
  default:
    console.log("I am"+ch);
  
}
```

## Loops

### for loop
```js
for(let x=0; x<=10; x++){
  console.log(x);
}
```

### while loop
```js
let x=0;
while(x<=10){
  console.log(x);
  x++;
}
```

### do...while Loop
```js
let x=0;
do {
  console.log(x);
  x++;
}while(x<=10);
```

### for...in loop
```js
let obj = {
  a : 'a',
  b : 'b',
  c : 'c',
  d : 'd',
};
for(let x in obj){
  console.log(obj[x]);
}
```
### for...of loop
```js
let obj = {
  a : 'a',
  b : 'b',
  c : 'c',
  d : 'd',
};
for(let x of obj){
  console.log(x);
}
```

### forEach method
```js
let arr = [1, 2, 3, 4];
arr.forEach( data => {
  console.log(data);
});
```


## Functions

### Named Function

These are defined with the function keyword followed by the function name. They can be called before they are declared (due to hoisting).
```js
function myfunction(a,b){
    console.log(a+b);
}
```

### Anonymous Functions

These are functions without a name. They are commonly used as function expressions or as arguments to other functions.
```js
var newfun = function(a,b) {
    console.log(a+b);
}
```

### Arrow Functions
Introduced in ES6, arrow functions provide a concise syntax and lexical scoping of `this` keyword.
```js
var myfun = (a,b) => {
    console.log(a+b);
}
```

### Immediately Invoked Function Expressions (IIFE)
Functions that are executed immediately after they are created.
```js
(function (a,b){
  console.log(a+b);
}());
```

## Type Conversion

### Implicit Type Conversion (Type Coercion)
JavaScript automatically converts the data type of a value when needed. For example, when using the `+` operator with a string and a number, JavaScript will convert the number to a string and perform string concatenation.
```js
var num = 10;
var str = "The number is: " + num; // Implicit conversion of num to a string
```

### Explicit Type Conversion (Type Casting)
Developers can explicitly convert values from one type to another using conversion functions or operators.

#### String Conversion
You can convert values to strings using the `String()` function or the `.toString()` method.
```js
var num = 10;
var str = String(num);
```

### Number Conversion
You can convert values to numbers using the `Number()` function or the `parseInt()` and `parseFloat()` functions.
```js
var str = "10";
var num = Number(str);
```

### Boolean Conversion
Values can be converted to boolean using the `Boolean()` function.
```js
var str = "true";
var bool = Boolean(str);
```

## Try, Catch and Throw
In JavaScript, `try`, `catch`, and `throw` are keywords used for error handling. They help you manage errors gracefully within your code. 

### try Statement
The try statement allows you to specify a block of code to be tested for errors while it is being executed:
```js
try {
  // Code that may throw an error
} catch (error) {
  // Code to handle the error
}
```

### catch Clause
The catch clause is used to handle the error thrown in the try block. If any error occurs within the try block, the catch block will be executed:
```js
try {
  // Code that may throw an error
} catch (error) {
  // Code to handle the error
  console.log("An error occurred:", error.message);
}
```

### throw Statement
The throw statement allows you to create a custom error. It can be used inside the try block to manually generate an error:
```js
try {
  // Code that may throw an error based on some condition
  if (condition) {
    throw new Error("Custom error message");
  }
} catch (error) {
  // Code to handle the error
  console.log("An error occurred:", error.message);
}
```

## Lexical scope
Lexical scope is a concept in JavaScript that describes how variable and function names are resolved during the compilation phase. It determines the visibility and accessibility of variables and functions within nested scopes based on the location of the code within the source code.

In lexical scope (also known as static scope), the visibility of variables and functions is determined by their placement in the source code. When a function is defined within another function, the inner function has access to the variables and functions defined in the outer function's scope, as well as any scopes that enclose it. However, the outer function does not have access to the variables and functions defined within the inner function's scope.

```js
function outerFunction() {
    var outerVariable = "I am from outerFunction";

    function innerFunction() {
        var innerVariable = "I am from innerFunction";
        console.log(outerVariable); // Accessible
    }

    innerFunction();
    // console.log(innerVariable); // Not accessible
}

outerFunction();
```

## Class
In JavaScript, you can create classes using the ES6 class syntax. Classes provide a more familiar and cleaner syntax for defining object blueprints compared to the traditional prototype-based inheritance.

```js
class MyClass {
  constructor(property1, property2) {
    this.property1 = property1;
    this.property2 = property2;
  }

  method1() {
    console.log('Method 1');
  }

  method2() {
    console.log('Method 2');
  }
}
```

- MyClass is the class name.
- constructor is a special method for creating and initializing objects created with a class.
- method1 and method2 are methods defined in the class.

```js
let instance = new MyClass('value1', 'value2');
instance.method1(); // Output: Method 1
console.log(instance.property1); // Output: value1
```

### Inheritance

```js
class MySubClass extends MyClass {
  constructor(property1, property2, property3) {
    super(property1, property2);
    this.property3 = property3;
  }

  method3() {
    console.log('Method 3');
  }
}
```

## Synchronous and Asynchronous Programming:

### Synchronous Programming
In synchronous programming, code is executed sequentially, one statement at a time. Each statement waits for the previous one to complete before executing. Synchronous code is straightforward and easier to understand, as the flow of execution is predictable.
```js
console.log('Statement 1');
console.log('Statement 2');
console.log('Statement 3');

/*
Statement 1
Statement 2
Statement 3
*/
```

### Asynchronous Programming
In asynchronous programming, tasks can be executed independently of the main program flow. Asynchronous operations are non-blocking, meaning that while an operation is being performed, the program can continue to execute other tasks. Callback functions, Promises, and async/await are common techniques used for handling asynchronous code in JavaScript.

```js
console.log('Statement 1');

setTimeout(function() {
    console.log('Statement 2');
}, 1000);

console.log('Statement 3');

/*
Statement 1
Statement 3
Statement 2
*/
```

### Promises and async/await
Promises and async/await are modern JavaScript features for handling asynchronous code in a more readable and manageable way.

#### Promise

```js
console.log('Statement 1');

new Promise(function(resolve, reject) {
    setTimeout(function() {
        console.log('Statement 2');
        resolve();
    }, 1000);
}).then(function() {
    console.log('Statement 3');
});
```

#### Async/Await

```js
async function myFunction() {
    console.log('Statement 1');
    
    await new Promise(function(resolve) {
        setTimeout(function() {
            console.log('Statement 2');
            resolve();
        }, 1000);
    });

    console.log('Statement 3');
}

myFunction();
```

Asynchronous programming is commonly used in JavaScript for tasks such as fetching data from servers, handling user input, and performing time-consuming operations without blocking the main thread.

## API Calls
In JavaScript, you can make API calls using various methods, such as the `XMLHttpRequest object`, the `fetch()` API, or third-party libraries like Axios. 

### Using XMLHttpRequest
```js
var xhr = new XMLHttpRequest();
xhr.open('GET', 'https://api.example.com/data', true);
xhr.onreadystatechange = function() {
    if (xhr.readyState === 4 && xhr.status === 200) {
        var response = JSON.parse(xhr.responseText);
        console.log(response);
    }
};
xhr.send();
```

### Using fetch() API (modern approach)
```js
fetch('https://api.example.com/data')
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
```

### Using Axios (third-party library):
First, include Axios in your project:
```js
<script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
```

```js
axios.get('https://api.example.com/data')
    .then(response => console.log(response.data))
    .catch(error => console.error('Error:', error));
```

## DOM

### Add Listener Event

In JavaScript, the addEventListener method is used to attach an event handler to an element. This allows you to specify a function to be executed when a particular event occurs on the element. 

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Event Listener Example</title>
</head>
<body>
    <button id="myButton">Click Me</button>

    <script>
        // Get a reference to the button element
        var button = document.getElementById('myButton');

        // Add an event listener to the button for the 'click' event
        button.addEventListener('click', function() {
            alert('Button clicked!');
        });
    </script>
</body>
</html>
```





# Layouts
how the text, image and other content is placed over a webpage.

## Types of layout
Arranging the different elements in an organized manner.

### Page Layout
Arranging the different components of the page.

### Component Layout
Arranging the different elements of the components.

## Way of building layout

### Using Float
The old way of building layouts of all sizes uses the float CSS property. Still used, but getting outdated fast.

-Elements are removed from the normal flow: "out of flow"

- Text and inline elements will wrap around the floated elements.

- The container will not adjust its height to the element. This is known as **collapsing of heights**.

- The container will not adjust its width to the element, and so it will put all the elements down if they are taking higher dimensions than the available ones.

```css
Selector {
  float: left; /*will take element out from normaal flow and put them in left of the flow. */
  float: right; /*will take element out from normaal flow and put them in right of the flow. */
}
```

#### Clearing floats
To avoid the problem of collapsing height we can use one trick.

1. Add an empty div with clear property

    Add an empty div inside the container, and in the style of that empty container add the clear property of CSS.
    ```css
    selector {
      clear: left; /* for left float*/
      clear: right; /* for right float*/
      clear: both; /* for both*/
    }
    ```

2. Using pseudo-element **after**
    Instead of adding an empty div to solve the problem of collapsing height, we can add a "clearfix" class in the container and add the following properties
    ```css
    .clearfix::after {
      content:"";
      clear:both;
      display:block;
    }
    ```

#### Higher width issue
This problem arises because of the box model, as the margin and the padding get added for the dimension of the element, we can use the property box-sizing to solve this issue. This will adjust the margin and padding, and hence overall dimension will be the same as the content.
```css
selector{
  box-sizing: border-box;
}
```

### Using Flexbox
The modern way of laying out elements in a 1-dimensional row without using floats. Perfect for component layouts.

Any container element, having some child can be used for flexbox. In this, the display property of the container is set to flex. This causes the elements to get horizontally aligned inside the container. All children will occupy only the required size.

```css
.container {
  display: flex;
}
```
1. Flexbox is a set of related CSS properties for building 1-dimensional layouts.
2. The main idea behind flexbox is that space inside a container element can be automatically divided by its child elements.
3. Flexbox makes it easy to automatically align items to one another inside a parent container, both horizontally and vertically.
4. flexbox solves common problems such as vertical centering and creating equal-height columns.
5. Flexbox is perfect for replacing floats, allowing us to write fewer and cleaner HTML and CSS code.

Container Element -> Flex container
Child Elements -> Flex items
Horizontal axis -> Main axis
Vertical axis -> Cross axis

#### CSS properties for Flex Container

1. **gap:0 | < length >**: To create space between items, without using a margin.
2. **justify-content: flex-start | flex-end | center | space-between | space-around | space-evenly**: align items along the main axis (horizontally, by default)
3. **align-items: stretch | flex-start | flex-end | center | baseline**: To align items along the cross axis (vertically, by default)
4. **flex-direction: row | row-reverse | column | column-reverse**: To define which is the main axis
5. **flex-wrap:nowrap | wrap | wrap-reverse**: To allow items to wrap into a new line if they are too large
6. **align-content: stretch | flex-start | flex-end | center | space-between | space-around**: only applies when there are multiple lines (flex-wrap: wrap)

#### CSS properties for Flex Items

1. **align-self: auto | stretch | flex-start | flex-end | baseline** : To overwrite align-items for individual flex items
2. **flex-grow: 0 | < integer >**: To allow an element to growing (0 means No, 1+ means Yes)
3. **flex-shrink: 0 | < integer >**: To allow an element to shrink (0 means no, 1+ means yes)
4. **flex-basis: auto | < length >**: To define an item's width, instead of the width property
5. **flex: 0 1 auto | < int > < int > < length >** : Recommended shorthand for flex-grow, flex-shrink, flex-basis
6. **order : 0 | < integer >**: 
  Controls order of items, -1 makes item first, 1 makes it last




### Using CSS-grid
For laying out elements in a full-fledged 2-dimensional grid. Perfect for page layouts and complex components.

```css
.container {
  display:grid;
  grid-template-columns:1px 2px 3px ;
  grid-template-rows:1px 2px 3px ;
  grid-gap:1px;
  column-gap:1px;
  row-gap;1px;
}
```

- CSS Grid is a set of CSS properties for building 2-dimensional layouts
- The main idea behind the CSS grid is that we divide a container element into rows and columns that can be filled with its child elements.
- In two-dimensional contexts, CSS grid allows us to write less nested HTML and easier-to-read CSS
- CSS Grid is not meant to replace flexbox! instead, they work perfectly together.

1-D layout -> Use flexbox
2-D layout -> Use CSS grid

display: grid;
container: Grid Container;
element: Grid items;
Horizontal axis: Row Axis;
Vertical axis: Column Axis
Grid lines: separating cells of grids
Grid cell: one cell
Grid track/row: a horizontal row of grid
Grid track/columns: vertical column of grids
Gutters: space between cells (gaps)

#### Grid Containers properties
1. grid-template-rows: < track size > *
2. grid-template-columns: < track size > *
3. row-gap: 0 | < length >
4. column-gap: 0 | < length >
5. justify-items: stretch | start | center | end: **align-items inside rows (horizontally)**
6. align-items: stretch | start | center | end: **align-items inside columns (vertically)**
7. justify-content: stretch | start | center | end: **align the entire grid inside the grid container (horizontally) if the container is larger than the grid.**
6. align-content: stretch | start | center | end: **align the entire grid inside the grid container (vertically) if the container is larger than the grid.**

#### Grid Items properties
1. grid-column: < start line > / < end line > | span < number >: **To place a grid item into a specific cell, based on line numbers. span keyword can be used to span an item across more cells.**
2. grid-row: < start line > / < end line > | span < number >: **To place a grid item into a specific cell, based on line numbers. span keyword can be used to span an item across more cells.**
3. justify-self: stretch | start | center | end : **To overwrite justify-items for single item;**
4. align-self: stretch | start | center | end : **To overwrite align-items for single items;**

In **grid-template-rows** and **grid-template-columns** instead of using **Npx**, you can use **Xfr**, where X means Xth fraction of the total size. If you put **auto** then it will automatically adjust according to the remaining space.

#### repeat function of CSS
```css
.container {
  display:grid;
  grid-template-columns: repeat(4, 1fr); /* This will create grid-template-columns: 1fr 1fr 1fr 1fr; */
}
```

#### using grid-column and grid-row
```css
.element--4{
  grid-column: 2 / 3; /* This will move to the grid item to 2nd column */
  grid-row: 1 / 2; /* This will move to the grid item to 1st row */
}

.element--4{
  grid-column: 2; /* This will move to the grid item to 2nd column */
  grid-row: 1; /* This will move to the grid item to 1st row */
}

.element--4{
  grid-column: 2 / 5; /* This will move to the grid item from 2nd column to 5th column*/
  grid-row: 1 / 3; /* This will move to the grid item from 1st row to 4rd row*/
}

.element--4{
  grid-column: 2 / span 3; /* This will move to the grid item from 2nd column 2nd + 3 column*/
  grid-row: 1 / span 3; /* This will move to the grid item from 1st row to 1st + 3 row*/
}

.element--4{
  grid-column: 1 / -1; /* This will cover the whole column*/
  grid-row: 1 / -1; /* This will cover the whole row*/
}
```

# Web Design Rules and Framework

## Web Design Ingredients

1. **Typography**
2. **Colors**
3. **Images/illustration**
4. **Icons**
5. **Shadows**
6. **Border-radius**
7. **Whitespace**
8. **Visual Hierarchy**
9. **User Experience**
10. **Components/layout**

## Website Personality

1. **Serious/Elegant**: For luxury and elegance, based on thin serif typefaces, golden or pastel colors, and big high-quality images.

2. **Minimalist/Simple**: Focuses on the essential text content, using small or medium-sized sans-serif black text, lines, and a few images and icons.

3. **Plain/Neutral**: Design that gets out of the way by using neutral and small typefaces, and a very structured layout. Common in big corporations.

4. **Bold/Confident**: Makes an impact, by featuring big and bold typography, paired with the confident use of big and bright colored boxes.

5. **Calm/Peaceful**: For products and services that care, transmitted by calming pastel colors, soft serif headings, and matching images/illustrations.

6. **Startup/Upbeat**: Widely used in startups, featuring medium-sized sans-serif typefaces, light-gray text and backgrounds, and rounded elements.

7. **Playful/Fun**: Colorful and round design, fueled by creative elements like hand-drawn icons or illustrations, animations, and fun language. 


## Typography

<blockquote>
Typography is the art and technique of arranging type to make written language legible, readable and appealing when displayed.        --Wikipedia
</blockquote>

**Serif**
1. Has a tail at all the corners of the letter.
2. Creates a traditional classic look  and feel
3. Conveys trustworthiness
4. Good for long text
Example
> <b style="font-family:serif;">This is a Serif text.</b>

**Sans-Serif**
1. No tail at any corner of the letter.
2. Modern  and feel
3. Clean and simple
4. Easier to choose for beginner designer!
Example
> <b style="font-family:sans-serif;">This is a Serif text.</b>



### Rule:1 Use Good Typefaces

1. Use only good and popular typefaces and play it safe

2. It's ok to use just one typeface per page! If you want more, limit to 2 typefaces.

3.  Choose the right typeface according to your website personality

<blockquote>

SANS-SERIF
  - Inter
  - Open Sans
  - Roboto
  - Monsterrat
  - Work Sans
  - Lato

  SERIF
  - Merriweather
  - Aleo
  - Playfair Display
  - Cormorant
  - Cardo
  - Lora

Toolbox: **Google fonts, and Font Squirrel**

</blockquote>

### Rule:2 Use  Good Font Sizes and Weights

4. When choosing font sizes, limit choices! Use a "type scale" tool or other pre-defined range

5. Use a font size between 16px and 32px for normal text

6. For long text (like a blog post), try a size of 20px or even bigger

7. for headlines, you can go big (50px+) and bold (600+), depending on the personality

8. For any text, don't use a font-weight under 400 (regular)

<blockquote>
FONT SIZE SYSTEM (px)

10 / 12 / 14 / 16 / 18 / 20 / 24 / 30 / 36 / 44 / 52 / 62 / 74 / 86 / 98
</blockquote>

### Rule:3 Create a Good Reading Experience

9. Use less than 75 characters per line

10. For normal-sized text, use a line height between 1.5 and 2. for big text, go below

    The smaller or longer the text, the larger the height needs to be!

11. Decrease letter spacing in headlines, if it looks unnatural

12. Experiment with all caps for short titles. Make them small and bold and increase the letter spacing

13. Usually, don't justify text

14. Don't center long text blocks. Small blocks are fine.

<blockquote>
SPACING SYSTEM (px)

2 / 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 80 / 96 / 128
</blockquote>

## COLORS

### Rule:4 Choose the Right Color

1. Make the main color match your website's personality: colors convey meaning!

    - <span style="margin-right:2px;background-color:red;">Red</span> draws a lot of attention and symbolizes power, passion, and excitement

    - <span style="margin-right:2px;background-color:orange;color:black;">Orange</span> is less aggressive and conveys happiness, cheerfulness, and creativity

    - <span style="margin-right:2px;background-color:yellow;color:black;">Yellow</span> means joy, brightness, and intelligence

    - <span style="margin-right:2px;background-color:green;">Green</span> represents harmony, nature, growth, and health

    - <span style="margin-right:2px;background-color:blue;">Blue</span> is associated with peace, trustworthiness, and professionalism

    - <span style="margin-right:2px;background-color:purple;">Purple</span> conveys wealth, wisdom, and magic

    - <span style="margin-right:2px;background-color:pink;color:black;">Pink</span> represents romance, care, and affection

    - <span style="margin-right:2px;background-color:brown;">Brown</span> is associated with nature, durability and comfort

    - <span style="margin-right:2px;background-color:black;"> Black</span> symbolizes power elegance and minimalism, but also grief and sorrow

2. Use a good color tone! Don't choose a random tone or CSS named colors.

    > TOOLBOX : **Open color, tailwindcss, flat ui colors 2**

### Rule:5 Establish a Color System

3. You need at least two types of colors in your color palette: the main color and the grey color, you can use 

4. With more experience, you can add more colors: accent colors (use a tool)

5. For diversity, create lighter and darker versions (tint and shades)

    > TOOLBOX: **Tint & Shade Generator, pallenton.com, coolors**

### Rule:6 When and How to use COLORS

6. Use your main color to draw attention to the most important elements on the page

7. Use colors to add interesting accents or make entire component or section stand out

8. You can try to use your color strategically in images and illustrations.

### Rule:7 Colors and Typography

9. On dark-colored backgrounds, try to use a tint of the background (" lighter version") for text

10. The text should usually not be completely black. Lighten it up it looks heavy and uninviting

11. Don't make the text too light! Use a tool to check the contrast between text and background colors
<blockquote>
The contrast ratio needs to be at least 4.5:1 for normal text and 3:1 for large text (18px+)

TOOLBOX: **coolors**
</blockquote>

## Images/illustration

### Rule:8 Use Good Images

1. Different types of images: product images, storytelling photos, illustrations, patterns

2. Use images to support your website's message and story. So only use relevant images!

3. Prefer original images. If not possible, use original-looking stock images (not generic ones!)

    <blockquote>

    TOOLBOX: **Unsplash, Pexels, DrawKit, unDraw**
    </blockquote>

### Rule:9 Use Images Well

4. Try to show real people to trigger the user's emotions

5. If necessary, crop images to fit your message

6. Experiment with combining photos, illustrations and patterns

### Rule:10 Handling Text on Images

7. Method #1: Darker or brighten the image (completely or partially using a gradient)

8. Method #2: Position text into a neutral image area

9. Method #3: Put text in a box

### Rule:11 Some Technical Details

10. To account for high-res screens, make image dimensions 2X as big as their displayed size.

- Scale factor: Actual pixels the screen contains / pixels represented on the screen

- On high-res screens, scale factor is 2X or even 3X, on normal screens it's just 1x (1 physical pixel = 1 design pixel)

11. Compress images for lower file size and better performance

    <blockquote>

    TOOLBOX: **Squash**
    </blockquote>

12. When using multiple images side-by-side, make sure they have the same dimensions

## Icons

### Rule:12 Use Good Icons

1. Use a good icon pack, there are tons of free and paid icons packs.

<blockquote>

TOOLBOX: **Phosphor icons, ionicons, icons8**
</blockquote>

2. Use only one icon pack, Don't mix icons from different icon packs

3. Use SVG icons or icon fonts. Don't use bitmap images formats (.jpg and .png)

- BITMAP
	- Regular Images, PNG, JPG and GIF
	- Do not scale, become unsharp!
- Vector-Based
	- SVG images and icon fonts
	- Scale indefinitely

4. Adjust to website personality! Roundness, weight and filled/outlined depend on typography


### Rule:13 When to use ICONS

5. Use icons to provide visual assistance to text

6. Use icons for product feature blocks

7. Use icons associated with actions, and label them (unless no space or icon is 100% clear)

8. Use icons as bullet points

### Rule:14 Use ICONS well

9. To keep icons neutral, use the same color as the text, to draw attention, use different color

10. Don't confuse your users: icons need to make sense and fit the text or action!

11. Don't make icons larger than what they were designed for. If needed, enclose them in a shape.

12. Use the stroke property to change the outline and fill to change the filled color of the SVG.
```css
.icon-1{
  stroke:blue;
  fill:red;
}
```

## Shadows

- After an era of 100% flat design, we are now back to using shadows in UI design (flat design 2.0)

- Shadow creates depth (3D): The more shadow, the further away from the interface element.

- Shadow can be used on boxes and text.

### Rule:15 Use SHADOWS WELL

1. You don't have to use shadows! Only use them if it makes sense for the website personality.

2. Use shadows in small doses: don't add shadows to every element!

3. Go light on shadows, don't make them too dark!

### Rule:16 Use SHADOWS in the RIGHT SITUATION

4. Use small shadows for smaller elements that should stand out (to draw attention)

5. Use medium-sized shadows for larger areas that should stand out a bit more

6. Use large shadows for elements that should really float above the interface.

7. Experiment with changing shadows on mouse interaction (click and hover)

    Normal -> Flat
    Hover -> Medium-sized shadow
    Click -> Smaller shadow

8. Experiment with glows (colored shadows)

```css
.container {
box-shadow: 20px 20px 20px 20px COLOR;
}
```
```css
.container {
text-shadow: 20px 20px 20px COLOR;
}
```

## Border-Radius

### Rule:17 Use BORDER_RADIUS Well

1. Use border-radius to increase the playfulness and fun of the design, to make it less serious.

2. The typeface has a certain roundness: make sure that the border radius matches that roundness!

3. Use border-radius on buttons, images, around icons, standout sections and other elements

    ```css
    .container {
    border-radius: 50px;
    }
    ```

## White Space

### Rule:18 When and Where to use WHITESPACE

- The right amount of whitespace makes designs look clean, modern and polished.

- Whitespace communicates how different pieces of information are related to one another.

- Whitespace implies invisible relationships between the elements of a layout.

1. Use tons of whitespace between sections

2. Use a lot of whitespace between groups of elements

3. Use whitespace between elements

4. Inside groups of elements, try to use whitespace instead of lines

### RULE:19 How much WHITE SPACE

5. The more some elements (or groups of elements) belong together, the closer they should be! **Law of Proximity**

6. Start with a lot of whitespaces, maybe even too much! Then remove whitespace from there.

	- Too much whitespace looks detached
	- Too little looks too crammed

7. Match other design choices. If you have big text or big icons, you need more whitespace

8. Try a hard rule, such as using multiples of 2px, 4px, 8px, and 16px for all spacing


## Visual Hierarchy

### Rule:20 What is Visual Hierarchy

- Visual Hierarchy is about establishing which elements of a design are the most important ones

- Visual hierarchy is about drawing attention to these most important elements

- Visual hierarchy is about defining a "path" for users, to guide them through the page

- We use a combination of position, size, colors, spacing, borders, and shadows to establish a meaningful visual hierarchy between elements/components

### RULE: 21 Visual Hierarchy Fundamentals

1. Position important elements closer to the top of the page, where they get more attention.

2. Use images mindfully, as they draw a lot of attention (larger images get more attention)

3. Whitespace creates separation, so use whitespace strategically to emphasize elements

### RULE:22 Visual Hierarchy for TEXT ELEMENTS

4. For text elements, use font size, font weight, color, and whitespace to convey the importance

5. What text elements to emphasize? Titles, sub-titles, links, buttons, data points, icons

	- You can also de-emphasize less important text, like labels or secondary/additional information

### RULE:23 Visual Hierarchy BETWEEN COMPONENTS

6. Emphasize an important component using background color, shadow, or border (or multiple)

7. Try emphasizing some component A over component B  by de-emphasizing component B.

8. What components to emphasize? Testimonials, call-to-action sections, highlight sections, preview cards, forms, pricing tables, important rows/columns in tables, etc.

## USER EXPERIENCE

### RULE:24 What is USER EXPERIENCE (UX)?

<blockquote>
Design is not just what it looks like and feels like. Design is how it works.    -- Steve Jobs
</blockquote>

- User Interface (UI) is the visual presentation of a product. It's how the graphical interface looks and feels.

- User Experience (UX) is the overall experience the user has while interacting with the product

### RULE:25 UI and UX Design

- UI is a graphical interface

- UI Design is what makes an interface beautiful

- UX experiences with interface

- UX design is what makes an interface useful and functional

- UX design can not exist without UI Design

### RULE:26 UX Design Guiding Principle: GOALS

- A website or application exists for a reason: a user has a goal for visiting it, and a goal for creating it.

- Good UX design aligns the user's goals with the business goals

### RULE:27 UX Rules for Usability

1. Don't design complicated layouts. Don't reinvent the wheel. Use patterns that users know.

2. Make your call-to-action the most prominent element, and make the descriptive

3. Use blue text and underlined text only for links!

4. Animations should have a purpose and be fast: between 200 and 500ms.

5. In forms, align labels and fields in a single vertical line, to make the form easier to scan

6. Offer users good feedback for all actions: form errors, form success, etc. [web apps]

7. Place action buttons where they will create an effect (law of locality) [Web Apps}


### RULE:28 UX Rules for Website Content

8. Use a descriptive, keyword-focused headline on your main page. Don't be vague or fancy!

9. Only include relevant information, efficiently! Cut out the fluff and make the content 100% clear.

10. Use simple words! Avoid technical jargon and "smart-sounding" words

11. Break up long text with sub-headings, images, block quotes, bullet points etc.


# Components and Layout Patterns

## From Elements to Webpage

Elements > Components > Layout > Webpage

1. Use common elements and components to convey your website's information

2. Combine components into layout using common layout patterns

3. Assemble different layouts into a complete, final page

## Elements

1. Text
2. Buttons
3. Images
4. Input Elements
5. Tags

## Components

1. Breadcrumbs
2. Pagination
3. Alert and status bars
4. Statistics
5. Gallery
6. Feature Box
7. Preview and profile cards
8. Accordion
9. Tabs
10. Carousel
11. Customer testimonials
12. Customer logos
13. Featured-in logos
14. Steps
15. Forms
16. Tables
17. Pricing tables
18. Modal windows

## Section Components

1. Navigation
2. Hero section
3. Footer
4. Call-to-action section
5. Feature row

## Layout Patterns
1. A row of boxes or cards
2. Grid of boxes or cards
3. Z-pattern
4. F-pattern
5. Single-column
6. Sidebar
7. Multi-column/magazine
8. Asymmetry/Experimental



# Responsiveness 

Add in HEAD
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

## Media Queries
```css
@media (max-width: 600px){
  /* write css rules */
}
 /* means "Is width <=600px?" */
```

## Breakpoints

### BAD 
Select the screen size of popular brands

### Good
Select between the different sizes

1. 600px
2. 900px
3. 1200px

### Best
Where your design breaks

> 1 rem = 1em =16px

> use vh, viewport height

> use vw, viewport width


```css
@media(max-width:100em/16*100px)
{
  .container{
    padding:10rem;
  }
}
```



> # REACT

Download and Install React, Node, NPM

## Creating an App

`npx create-react-app react_app`

`cd react_app`

`npm start`

## Structure of the App
```txt
drwxr-xr-x 1 iamjp 197609      0 Apr 12 16:27 ./
drwxr-xr-x 1 iamjp 197609      0 Apr 12 16:24 ../
drwxr-xr-x 1 iamjp 197609      0 Apr 12 16:27 .git/
-rw-r--r-- 1 iamjp 197609    310 Apr 12 16:25 .gitignore
drwxr-xr-x 1 iamjp 197609      0 Apr 12 16:27 node_modules/
-rw-r--r-- 1 iamjp 197609    812 Apr 12 16:27 package.json
-rw-r--r-- 1 iamjp 197609 718795 Apr 12 16:27 package-lock.json
drwxr-xr-x 1 iamjp 197609      0 Apr 12 16:27 public/
-rw-r--r-- 1 iamjp 197609   3359 Apr 12 16:26 README.md
drwxr-xr-x 1 iamjp 197609      0 Apr 12 16:27 src/
```

### README.md
All the commands and basic documentation are present in this file.

### package.json
list of dependencies needed to run the app.

### package-lock.json
It contains a list of other dependencies that are needed for the package defined in `package.json`

### .gitignore
To ignore files/directories that do not need to be pushed or to be part of the actual app.

### node_modules
Contains packages and module files. 

### src
Actual react app code, contains `css` and `js` files

### public
files and code that are publically available.

## Install dependencies
`npm i`

## The starting point for the app

You can see there are files in `src` folder, it has `index.js and index.css` also it has `App.js and App.css`. These files are the building blocks for the app.
- `*.js` : These files contain code that builds the basic structure of the app. It contains `javascript` code with tags that ultimately help to draw the HTML components.

- `*.css` These file contains the `css` code to style the corresponding `*.js` 

### `index.js`

```js
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

reportWebVitals();
```

`index.js` is the starting point, here we first get the root element of our page, using `const root = ReactDOM.createRoot(document.getElementById('root'));` and then we use `root.render(<React.StrictMode><App /></React.StrictMode>);` to render the `App.js`. All global css code is added in `index.css`

### `App.js`

```js
import logo from './logo.svg';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header>
    </div>
  );
}

export default App;
```

As in `index.js` we used `<App />` to render the code of `App.js`, same will be done for other `*.js`.

In `App.js` we have a function `App()` that returns an `HTML code block` and that is getting rendered by `index.js`

## REACT Components

### Creating your own App.js

1. Create one file in `src` `App.js`
2. Add below code in `App.js`
```js
function App(){
  return (
    <h1>Hello, I am a component</h1>
  )
}

export default App;
```
3. In `index.js` add the below import statment
```js
import App from './App';
````
and below code
```js
<App />
```

## Introduction to JSX

`JSX : JavaScript XML` This allows to write HTML code in react.

### adding any variable
```jsx
function App(){
  let a= 23;
  return (
    <h1> Value of a is {a}</h1>
  )
}
```

### adding style in elements
the style will be in camel case, eg ~~background-color~~ > backgroundColor
```jsx
function App(){
  let a= 23;
  return (
    <h1 style={{backgroundColor:"blue"}}> Value of a is {a}</h1>
  )
}
```

### className
all properties of css will be camel case, ~~class~~ `className`


## PROPS
These can be used to pass values to components.

```jsx
// Component.js
import React from "react";
import Component from "./Component"

export default function ComponentList(){
  students = [
    {
      name: "Akshat",
      age:18,
      gender: "Male",
      school: "Delhi Public School"
    },
    {
      name: "Pallav",
      age:19,
      gender: "Male",
      school: "Kendriya Vidyalaya"
    },
    {
      name: "Shubh",
      age:18,
      gender: "Male",
      school: "FGIET"
    }
  ]
  return (
    <div>
      students.map((ele) => {
        return <Component 
          name={ele.name}
          age={ele.age}
          gender={ele.gender}
          school={ele.school}
        />
      })
    </div>
  )
}

// Component.js
import React from "react";

export default function Component(props){
  const {name,age,gender,school} = props;
  return (
    <div>
      <div>
        <h2>{name}</h2>
      </div>
      <div>
        <h4>{age}</h4>
        <h4>{gender}</h4>
        <h4>{school}</h4>
      </div>
    </div>
  )
}
```

## State


