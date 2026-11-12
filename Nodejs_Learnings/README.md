# NODE

## About Node

**Node.js** is a cross-platform runtime environment and library for running JavaScript applications outside the browser.

*Node.js is a platform built on Chrome's JavaScript runtime for easily building fast and scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.*

<img src="https://www.javatpoint.com/js/nodejs/images/what-is-nodejs.png" alt="parts of node"/>


`Node.js = Runtime Environment + JavaScript Library`

### Features of Node.js

1. **Extremely fast**: Node.js is built on Google Chrome's V8 JavaScript Engine, so its library is very fast in code execution.
2. **I/O is Asynchronous and Event Driven**: All APIs of Node.js library are asynchronous i.e. non-blocking. So a Node.js based server never waits for an API to return data. The server moves to the next API after calling it and a notification mechanism of Events of Node.js helps the server to get a response from the previous API call. It is also a reason that it is very fast.
3. **Single threaded**: Node.js follows a single threaded model with event looping.
4. **Highly Scalable**: Node.js is highly scalable because event mechanism helps the server to respond in a non-blocking way.
5. **No buffering**: Node.js cuts down the overall processing time while uploading audio and video files. Node.js applications never buffer any data. These applications simply output the data in chunks.
6. **Open source**: Node.js has an open source community which has produced many excellent modules to add additional capabilities to Node.js applications.
7. **License**: Node.js is released under the MIT license.


## Installation and Best Practices

### Installation

`sudo apt-get install nodejs npm`

`brew install nodejs`

`npm install package_name`

### Best Coding Practices

1. Use `'` for string in node.


## Node | Basic Understanding


### Logging | Printing

#### Normal String Logging
```js
console.log('Hello World!');
console.error('Error logging');
console.warn('Warning logging');
```

Output:
```txt
Hello World!
Error logging
Warning logging
```

### Logging with variable
```js
console.log('Value of a is %s.', 'a');
```
Output:
```txt
Value of a is a.
```
### Error Logging

```js
console.error(new Error('Hell! This is a sample error.'));
```
Output:
```txt
Error: Hell! This is a sample error.
```

### REPL Environment
The Node.js or node come bundled with REPL environment. Each part of the REPL environment has a specific work.

- **Read**: It reads user's input; parse the input into JavaScript data-structure and stores in memory.

- **Eval**: It takes and evaluates the data structure.

- **Print**: It prints the result.

- **Loop**: It loops the above command until user press ctrl-c twice.

<table class="alt">
    <tbody>
        <tr>
            <td>Commands</td>
            <td>Description</td>
        </tr>
        <tr>
            <td>ctrl + c</td>
            <td>It is used to terminate the current command.</td>
        </tr>
        <tr>
            <td>ctrl + c twice</td>
            <td>It terminates the Node REPL.</td>
        </tr>
        <tr>
            <td>ctrl + d</td>
            <td>It terminates the Node REPL.</td>
        </tr>
        <tr>
            <td>up/down keys</td>
            <td>It is used to see command history and modify previous commands.</td>
        </tr>
        <tr>
            <td>tab keys</td>
            <td>It specifies the list of current commands.</td>
        </tr>
        <tr>
            <td>.help</td>
            <td>It specifies the list of all commands.</td>
        </tr>
        <tr>
            <td>.break</td>
            <td>It is used to exit from multi-line expressions.</td>
        </tr>
        <tr>
            <td>.clear</td>
            <td>It is used to exit from multi-line expressions.</td>
        </tr>
        <tr>
            <td>.save filename</td>
            <td>It saves the current Node REPL session to a file.</td>
        </tr>
        <tr>
            <td>.load filename</td>
            <td>It is used to load file content into the current Node REPL session.</td>
        </tr>
    </tbody>
</table>



### Import modules

```js
var http = require('http');
```

### Data Types

Types of data used in node.

**Types of data**

1. **string**
2. **boolean**
3. **integer**
4. **float**
5. **null**
6. **undefined**

### Node.js OS

<table>
    <tbody>
        <tr
            td>
                <div id="bottomnextup">
                    <a class="next" href="nodejs-timer">next →</a>
                    <a class="next" href="nodejs-package-manager">← prev</a>
                </div>
                <h1 class="h1">Node.js OS</h1>
                <p>Node.js OS provides some basic operating-system related
                    utility functions. Let's see the list generally used
                    functions or methods.</p>
                <table class="alt">
                    <tbody><tr>
                            <th>Index</th>
                            <th>Method</th>
                            <th>Description</th>
                        </tr>
                        <tr>
                            <td>1.</td>
                            <td>os.arch()</td>
                            <td>This method is used to fetch the operating
                                system CPU architecture.</td>
                        </tr>
                        <tr>
                            <td>2.</td>
                            <td><div>os.cpus()</div></td>
                            <td>This method is used to fetch an array of objects
                                containing information about each cpu/core
                                installed: model, speed (in MHz), and times (an
                                object containing the number of milliseconds the
                                cpu/core spent in: user, nice, sys, idle, and
                                irq).</td>
                        </tr>
                        <tr>
                            <td>3.</td>
                            <td>os.endianness()</td>
                            <td>This method returns the endianness of the cpu.
                                Its possible values are 'BE' for big endian or
                                'LE' for little endian.</td>
                        </tr>
                        <tr>
                            <td>4.</td>
                            <td>os.freemem()</td>
                            <td>This methods returns the amount of free system
                                memory in bytes.</td>
                        </tr>
                        <tr>
                            <td>5.</td>
                            <td>os.homedir()</td>
                            <td>This method returns the home directory of the
                                current user.</td>
                        </tr>
                        <tr>
                            <td>6.</td>
                            <td><div>os.hostname()</div></td>
                            <td>This method is used to returns the hostname of
                                the operating system.</td>
                        </tr>
                        <tr>
                            <td>7.</td>
                            <td>os.loadavg()</td>
                            <td>This method returns an array containing the 1,
                                5, and 15 minute load averages. The load average
                                is a time fraction taken by system activity,
                                calculated by the operating system and expressed
                                as a fractional number. </td>
                        </tr>
                        <tr>
                            <td>8.</td>
                            <td>os.networkinterfaces()</td>
                            <td>This method returns a list of network
                                interfaces.</td>
                        </tr>
                        <tr>
                            <td>9.</td>
                            <td>os.platform()</td>
                            <td>This method returns the operating system
                                platform of the running computer i.e.'darwin',
                                'win32','freebsd', 'linux', 'sunos' etc.</td>
                        </tr>
                        <tr>
                            <td>10.</td>
                            <td>os.release()</td>
                            <td>This method returns the operating system
                                release.</td>
                        </tr>
                        <tr>
                            <td>11.</td>
                            <td>os.tmpdir()</td>
                            <td>This method returns the operating system's
                                default directory for temporary files.</td>
                        </tr>
                        <tr>
                            <td>12.</td>
                            <td>os.totalmem()</td>
                            <td>This method returns the total amount of system
                                memory in bytes.</td>
                        </tr>
                        <tr>
                            <td>13.</td>
                            <td>os.type()</td>
                            <td>This method returns the operating system name.
                                For example 'linux' on linux, 'darwin' on os x
                                and 'windows_nt' on windows.</td>
                        </tr>
                        <tr>
                            <td>14.</td>
                            <td>os.uptime()</td>
                            <td>This method returns the system uptime in
                                seconds.</td>
                        </tr>
                        <tr>
                            <td>15.</td>
                            <td>os.userinfo([options])</td>
                            <td>This method returns a subset of the password
                                file entry for the current effective user.</td>
                        </tr>
                    </tbody></table>
                <h2 class="h2">Node.js OS Example 1</h2>
                <p>In this example, we are including some basic functions.
                    Create a file named os_example1.js having the following
                    code:</p>
                <p class="filename">File: os_example1.js</p>
                <div class="codeblock"><div class="dp-highlighter"><div
                            class="bar"><div class="tools"><a href="#"
                                    onclick="dp.sh.Toolbar.Command('ViewSource',this);return false;"></a><a
                                    href="#"
                                    onclick="dp.sh.Toolbar.Command('PrintSource',this);return false;"></a><a
                                    href="#"
                                    onclick="dp.sh.Toolbar.Command('About',this);return false;"></a></div></div><ol
                            start="1" class="dp-xml"><li
                                class="alt"><span><span>const&nbsp;</span><span
                                        class="attribute">os</span><span>=</span><span
                                        class="attribute-value">require</span><span>('os');&nbsp;&nbsp;</span></span></li><li
                                class><span>console.log("os.freemem():&nbsp;\n",os.freemem());&nbsp;&nbsp;</span></li><li
                                class="alt"><span>console.log("os.homedir():&nbsp;\n",os.homedir());&nbsp;&nbsp;</span></li><li
                                class><span>console.log("os.hostname():&nbsp;\n",os.hostname());&nbsp;&nbsp;</span></li><li
                                class="alt"><span>console.log("os.endianness():&nbsp;\n",os.endianness());&nbsp;&nbsp;</span></li><li
                                class><span>console.log("os.loadavg():&nbsp;\n",os.loadavg());&nbsp;&nbsp;</span></li><li
                                class="alt"><span>console.log("os.platform():&nbsp;\n",os.platform());&nbsp;&nbsp;</span></li><li
                                class><span>console.log("os.release():&nbsp;\n",os.release());&nbsp;&nbsp;</span></li><li
                                class="alt"><span>console.log("os.tmpdir():&nbsp;\n",os.tmpdir());&nbsp;&nbsp;</span></li><li
                                class><span>console.log("os.totalmem():&nbsp;\n",os.totalmem());&nbsp;&nbsp;</span></li><li
                                class="alt"><span>console.log("os.type():&nbsp;\n",os.type());&nbsp;&nbsp;</span></li><li
                                class><span>console.log("os.uptime():&nbsp;\n",os.uptime());&nbsp;&nbsp;</span></li></ol></div><textarea
                        name="code" class="xml" style="display: none;">const
                        os=require('os');
                        console.log("os.freemem(): \n",os.freemem());
                        console.log("os.homedir(): \n",os.homedir());
                        console.log("os.hostname(): \n",os.hostname());
                        console.log("os.endianness(): \n",os.endianness());
                        console.log("os.loadavg(): \n",os.loadavg());
                        console.log("os.platform(): \n",os.platform());
                        console.log("os.release(): \n",os.release());
                        console.log("os.tmpdir(): \n",os.tmpdir());
                        console.log("os.totalmem(): \n",os.totalmem());
                        console.log("os.type(): \n",os.type());
                        console.log("os.uptime(): \n",os.uptime());
                    </textarea></div>
                <p>Open Node.js command prompt and run the following code:</p>
                <div class="codeblock"><div class="dp-highlighter"><div
                            class="bar"><div class="tools"><a href="#"
                                    onclick="dp.sh.Toolbar.Command('ViewSource',this);return false;"></a><a
                                    href="#"
                                    onclick="dp.sh.Toolbar.Command('PrintSource',this);return false;"></a><a
                                    href="#"
                                    onclick="dp.sh.Toolbar.Command('About',this);return false;"></a></div></div><ol
                            start="1" class="dp-xml"><li
                                class="alt"><span><span>node&nbsp;os_example1.js&nbsp;&nbsp;</span></span></li></ol></div><textarea
                        name="code" class="xml" style="display: none;">node
                        os_example1.js
                    </textarea></div>
                <img src="js/nodejs/images/nodejs-os-example1.jpg"
                    alt="Node.js os example 1">
                <h2 class="h2">Node.js OS Example 2</h2>
                <p>In this example, we are including remaining functions. Create
                    a file named os_example2.js having the following code:</p>
                <p class="filename">File: os_example2.js</p>
                <div class="codeblock"><div class="dp-highlighter"><div
                            class="bar"><div class="tools"><a href="#"
                                    onclick="dp.sh.Toolbar.Command('ViewSource',this);return false;"></a><a
                                    href="#"
                                    onclick="dp.sh.Toolbar.Command('PrintSource',this);return false;"></a><a
                                    href="#"
                                    onclick="dp.sh.Toolbar.Command('About',this);return false;"></a></div></div><ol
                            start="1" class="dp-xml"><li
                                class="alt"><span><span>const&nbsp;</span><span
                                        class="attribute">os</span><span>=</span><span
                                        class="attribute-value">require</span><span>('os');&nbsp;&nbsp;</span></span></li><li
                                class><span>console.log("os.cpus():&nbsp;\n",os.cpus());&nbsp;&nbsp;</span></li><li
                                class="alt"><span>console.log("os.arch():&nbsp;\n",os.arch());&nbsp;&nbsp;</span></li><li
                                class><span>console.log("os.networkInterfaces():&nbsp;\n",os.networkInterfaces());&nbsp;&nbsp;&nbsp;</span></li></ol></div><textarea
                        name="code" class="xml" style="display: none;">const
                        os=require('os');
                        console.log("os.cpus(): \n",os.cpus());
                        console.log("os.arch(): \n",os.arch());
                        console.log("os.networkInterfaces(): \n",os.networkInterfaces());
                    </textarea></div>
                <p>Open Node.js command prompt and run the following code:</p>
                <div class="codeblock"><div class="dp-highlighter"><div
                            class="bar"><div class="tools"><a href="#"
                                    onclick="dp.sh.Toolbar.Command('ViewSource',this);return false;"></a><a
                                    href="#"
                                    onclick="dp.sh.Toolbar.Command('PrintSource',this);return false;"></a><a
                                    href="#"
                                    onclick="dp.sh.Toolbar.Command('About',this);return false;"></a></div></div><ol
                            start="1" class="dp-xml"><li
                                class="alt"><span><span>node&nbsp;os_example2.js&nbsp;&nbsp;</span></span></li></ol></div><textarea
                        name="code" class="xml" style="display: none;">node
                        os_example2.js
                    </textarea></div>
                <img src="js/nodejs/images/nodejs-os-example2.jpg"
                    alt="Node.js os example 2">
                <div class="nexttopicdiv">
                    <span class="nexttopictext">Next Topic</span><span
                        class="nexttopiclink"><a href="nodejs-timer">Node.js
                            Timer</a></span>
                </div>

                <br><br>
                <div id="bottomnext">
                    <a style="float:left" class="next"
                        href="nodejs-package-manager">← prev</a>
                    <a style="float:right" class="next" href="nodejs-timer">next
                        →</a>
                </div>
                <br><br>
            </td>
        </tr>
    </tbody>
</table>

### Server | Creating and Using It

```js
var http = require("http");  
http.createServer(function (request, response) {  
    // Send the HTTP header   
    // HTTP Status: 200 : OK 
    // Content Type: text/plain  
    response.writeHead(200, {'Content-Type': 'text/plain'}); 
    // Send the response body as "Hello World"  
    response.end('Hello World\n');  
}).listen(8081);  
// Console will print the message  
console.log('Server running at http://127.0.0.1:8081/'); 
```
