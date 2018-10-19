//Taken from https://medium.com/@fwouts/parsing-javascript-in-javascript-89c9dc45f961

const ts = require("typescript")

fs.readFile('d3.min.js', function (err, data) {
  if (err) {
    throw err; 
  }
  sourceCode = data.toString();
});

let __filename = 'test.tmp'

let tsSourceFile = ts.createSourceFile(
  __filename,
  sourceCode,
  ts.ScriptTarget.Latest
);

fs.writeFile("out.json", JSON.stringify(tsSourceFile.statements), function(e) {
    if(e) {
        console.log(e);
    }
}); 
