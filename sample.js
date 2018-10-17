//Taken from https://medium.com/@fwouts/parsing-javascript-in-javascript-89c9dc45f961

const ts = require("typescript")

let sourceCode = `
<code goes here>
`;

let __filename = 'test.tmp'

let tsSourceFile = ts.createSourceFile(
  __filename,
  sourceCode,
  ts.ScriptTarget.Latest
);

fs.writeFile("tew.json", JSON.stringify(tsSourceFile.statements), function(e) {
    if(e) {
        console.log(e);
    }
}); 
