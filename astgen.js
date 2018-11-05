//Used https://medium.com/@fwouts/parsing-javascript-in-javascript-89c9dc45f961
//requires typescript, fs

let sourceName = process.argv[2];
let targetName = process.argv[3];

const ts = require("typescript");
const fs = require("fs");

let sourceCode = ``;

fs.readFile(sourceName, function (err, data) {
    if (err) {
        console.log(err)
        throw err; 
    }
    console.log(data);
    sourceCode = data.toString();
    console.log(sourceCode);


    console.log("Loaded " + sourceName);
    
    console.log(sourceCode)
    console.log("Dumping")
    
    let tsSourceFile = ts.createSourceFile(
      '/tmp/test.tmp',
      sourceCode,
      ts.ScriptTarget.Latest
    )
    
    console.log(sourceCode);
    
    fs.writeFile(targetName, JSON.stringify(tsSourceFile.statements), function(e) {
        if(e) {
            console.log(e);
        }
    }); 
});
