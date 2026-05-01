# VB6 Tree-sitter Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap proleap-vb6-parser behind a tree-sitter-compatible Python API via a subprocess+JSON bridge, so agent code can navigate VB6 syntax trees using standard tree-sitter patterns.

**Architecture:** Python `Parser` spawns a fat jar via subprocess; Java serializes the ANTLR4 CST + proleap ASG into JSON; Python builds an in-memory `Node` tree from JSON. No JVM lives in the Python process.

**Tech Stack:** Java 17, ANTLR4, Jackson (jackson-databind), maven-shade-plugin; Python 3.10+, pytest, no runtime deps beyond stdlib.

---

## File Map

**Java — new files:**
- `src/main/java/io/proleap/vb6/cli/ASTJsonSerializer.java` — walks ANTLR4 CST + ASGElementRegistry, emits Jackson ObjectNode
- `src/main/java/io/proleap/vb6/cli/VbParserCLI.java` — main(), arg parsing, orchestration

**Java — modified files:**
- `pom.xml` — add `jackson-databind` dependency + `maven-shade-plugin`

**Python — all new, under `vb6-parser-python/`:**
- `vb6_parser/_errors.py` — ParseError, VbRuntimeError, InternalError
- `vb6_parser/_node.py` — Node class (full tree-sitter API surface)
- `vb6_parser/_tree.py` — Tree class
- `vb6_parser/_cursor.py` — TreeCursor class
- `vb6_parser/_jar.py` — locate bundled jar
- `vb6_parser/_parser.py` — Parser class (subprocess logic)
- `vb6_parser/__init__.py` — public exports
- `resources/` — jar goes here after build
- `pyproject.toml`
- `tests/test_basic.py`
- `tests/test_semantic.py`
- `tests/test_cursor.py`
- `tests/conftest.py`

---

## Task 1: Add Jackson + shade plugin to pom.xml

**Files:**
- Modify: `pom.xml`

- [ ] **Step 1: Add jackson-databind dependency**

In `pom.xml`, inside the `<dependencies>` block, add after the logback entry:

```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.16.1</version>
</dependency>
```

- [ ] **Step 2: Add maven-shade-plugin**

In `pom.xml`, inside `<build><plugins>`, add after the antlr4 plugin entry:

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-shade-plugin</artifactId>
    <version>3.5.1</version>
    <executions>
        <execution>
            <phase>package</phase>
            <goals><goal>shade</goal></goals>
            <configuration>
                <finalName>vb6parser</finalName>
                <transformers>
                    <transformer implementation="org.apache.maven.plugins.shade.resource.ManifestResourceTransformer">
                        <mainClass>io.proleap.vb6.cli.VbParserCLI</mainClass>
                    </transformer>
                </transformers>
                <filters>
                    <filter>
                        <artifact>*:*</artifact>
                        <excludes>
                            <exclude>META-INF/*.SF</exclude>
                            <exclude>META-INF/*.DSA</exclude>
                            <exclude>META-INF/*.RSA</exclude>
                        </excludes>
                    </filter>
                </filters>
            </configuration>
        </execution>
    </executions>
</plugin>
```

- [ ] **Step 3: Verify pom.xml compiles**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
mvn validate -q
```

Expected: no output (success).

- [ ] **Step 4: Commit**

```bash
git add pom.xml
git commit -m "build: add jackson-databind and maven-shade-plugin for fat jar"
```

---

## Task 2: Implement ASTJsonSerializer

**Files:**
- Create: `src/main/java/io/proleap/vb6/cli/ASTJsonSerializer.java`
- Create: `src/test/java/io/proleap/vb6/cli/ASTJsonSerializerTest.java`

- [ ] **Step 1: Write the failing test**

Create `src/test/java/io/proleap/vb6/cli/ASTJsonSerializerTest.java`:

```java
package io.proleap.vb6.cli;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.proleap.vb6.asg.metamodel.Module;
import io.proleap.vb6.asg.metamodel.Program;
import io.proleap.vb6.asg.params.VbParserParams;
import io.proleap.vb6.asg.params.impl.VbParserParamsImpl;
import io.proleap.vb6.asg.runner.VbParserRunner;
import io.proleap.vb6.asg.runner.impl.VbParserRunnerImpl;
import org.antlr.v4.runtime.ParserRuleContext;
import org.junit.Test;

import static org.junit.Assert.*;

public class ASTJsonSerializerTest {

    private static final String HELLO_WORLD =
        "Private Sub Command1_Click ()\n" +
        "   Text1.Text = \"Hello, world!\"\n" +
        "End Sub\n";

    @Test
    public void rootNodeHasTypeModule() throws Exception {
        Program program = parse(HELLO_WORLD, "HelloWorld");
        Module module = program.getModules().get(0);
        ASTJsonSerializer ser = new ASTJsonSerializer(program.getASGElementRegistry(), HELLO_WORLD);
        JsonNode root = ser.serialize((ParserRuleContext) module.getCtx(), null);
        assertEquals("module", root.get("type").asText());
        assertTrue(root.get("is_named").asBoolean());
    }

    @Test
    public void startPointIsZeroIndexed() throws Exception {
        Program program = parse(HELLO_WORLD, "HelloWorld");
        Module module = program.getModules().get(0);
        ASTJsonSerializer ser = new ASTJsonSerializer(program.getASGElementRegistry(), HELLO_WORLD);
        JsonNode root = ser.serialize((ParserRuleContext) module.getCtx(), null);
        assertEquals(0, root.get("start_point").get(0).asInt());
        assertEquals(0, root.get("start_point").get(1).asInt());
    }

    @Test
    public void subStmtHasSemanticKindSub() throws Exception {
        Program program = parse(HELLO_WORLD, "HelloWorld");
        Module module = program.getModules().get(0);
        ASTJsonSerializer ser = new ASTJsonSerializer(program.getASGElementRegistry(), HELLO_WORLD);
        JsonNode root = ser.serialize((ParserRuleContext) module.getCtx(), null);
        JsonNode subStmt = findFirstNodeOfType(root, "subStmt");
        assertNotNull("expected subStmt node", subStmt);
        assertFalse(subStmt.get("semantic").isNull());
        assertEquals("sub", subStmt.get("semantic").get("kind").asText());
        assertEquals("Command1_Click", subStmt.get("semantic").get("name").asText());
    }

    @Test
    public void ambiguousIdentifierInSubHasFieldNameName() throws Exception {
        Program program = parse(HELLO_WORLD, "HelloWorld");
        Module module = program.getModules().get(0);
        ASTJsonSerializer ser = new ASTJsonSerializer(program.getASGElementRegistry(), HELLO_WORLD);
        JsonNode root = ser.serialize((ParserRuleContext) module.getCtx(), null);
        JsonNode subStmt = findFirstNodeOfType(root, "subStmt");
        assertNotNull(subStmt);
        JsonNode nameChild = null;
        for (JsonNode child : subStmt.get("children")) {
            if ("name".equals(child.get("field_name").asText(null))) {
                nameChild = child;
                break;
            }
        }
        assertNotNull("expected child with field_name=name in subStmt", nameChild);
    }

    @Test
    public void bytesAreConsistent() throws Exception {
        Program program = parse(HELLO_WORLD, "HelloWorld");
        Module module = program.getModules().get(0);
        ASTJsonSerializer ser = new ASTJsonSerializer(program.getASGElementRegistry(), HELLO_WORLD);
        JsonNode root = ser.serialize((ParserRuleContext) module.getCtx(), null);
        int startByte = root.get("start_byte").asInt();
        int endByte = root.get("end_byte").asInt();
        assertTrue("end_byte >= start_byte", endByte >= startByte);
    }

    // helpers

    private Program parse(String code, String moduleName) throws Exception {
        VbParserParams params = new VbParserParamsImpl();
        VbParserRunner runner = new VbParserRunnerImpl();
        return runner.analyzeCode(code, moduleName, params);
    }

    private JsonNode findFirstNodeOfType(JsonNode node, String type) {
        if (type.equals(node.get("type").asText())) return node;
        JsonNode children = node.get("children");
        if (children != null) {
            for (JsonNode child : children) {
                JsonNode found = findFirstNodeOfType(child, type);
                if (found != null) return found;
            }
        }
        return null;
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
mvn test -pl . -Dtest=ASTJsonSerializerTest -q 2>&1 | tail -10
```

Expected: compilation error — `ASTJsonSerializer` not found.

- [ ] **Step 3: Create ASTJsonSerializer.java**

Create `src/main/java/io/proleap/vb6/cli/ASTJsonSerializer.java`:

```java
package io.proleap.vb6.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.proleap.vb6.VisualBasic6Parser;
import io.proleap.vb6.asg.metamodel.ASGElement;
import io.proleap.vb6.asg.metamodel.Module;
import io.proleap.vb6.asg.metamodel.Variable;
import io.proleap.vb6.asg.metamodel.VisibilityElement;
import io.proleap.vb6.asg.metamodel.NamedElement;
import io.proleap.vb6.asg.metamodel.registry.ASGElementRegistry;
import io.proleap.vb6.asg.metamodel.statement.function.Function;
import io.proleap.vb6.asg.metamodel.statement.sub.Sub;
import org.antlr.v4.runtime.ParserRuleContext;
import org.antlr.v4.runtime.Token;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.TerminalNode;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public class ASTJsonSerializer {

    private static final Set<String> PROC_RULES = new HashSet<>(Arrays.asList(
        "subStmt", "functionStmt", "propertyGetStmt", "propertyLetStmt", "propertySetStmt"
    ));

    private final ObjectMapper mapper = new ObjectMapper();
    private final ASGElementRegistry registry;
    private final int[] lineOffsets;

    public ASTJsonSerializer(ASGElementRegistry registry, String source) {
        this.registry = registry;
        this.lineOffsets = buildLineOffsets(source);
    }

    private int[] buildLineOffsets(String source) {
        java.util.List<Integer> offs = new java.util.ArrayList<>();
        offs.add(0);
        for (int i = 0; i < source.length(); i++) {
            if (source.charAt(i) == '\n') {
                offs.add(i + 1);
            }
        }
        return offs.stream().mapToInt(Integer::intValue).toArray();
    }

    private String getRuleName(ParserRuleContext ctx) {
        String simple = ctx.getClass().getSimpleName();
        return simple.endsWith("Context") ? simple.substring(0, simple.length() - 7) : simple;
    }

    private String getFieldName(ParserRuleContext parent, ParseTree child) {
        if (!(child instanceof VisualBasic6Parser.AmbiguousIdentifierContext)) return null;
        return PROC_RULES.contains(getRuleName(parent)) ? "name" : null;
    }

    private int byteOffset(int line1, int col) {
        int line0 = line1 - 1;
        if (line0 < 0 || line0 >= lineOffsets.length) return 0;
        return lineOffsets[line0] + col;
    }

    public ObjectNode serialize(ParseTree node, ParserRuleContext parentCtx) {
        ObjectNode obj = mapper.createObjectNode();

        if (node instanceof TerminalNode terminal) {
            Token tok = terminal.getSymbol();
            String text = tok.getText();
            int startByte = byteOffset(tok.getLine(), tok.getCharPositionInLine());
            int endByte = startByte + text.length();

            obj.put("type", text);
            obj.put("is_named", false);
            obj.set("start_point", pointNode(tok.getLine() - 1, tok.getCharPositionInLine()));
            obj.set("end_point", pointNode(tok.getLine() - 1, tok.getCharPositionInLine() + text.length()));
            obj.put("start_byte", startByte);
            obj.put("end_byte", endByte);
            obj.put("field_name", parentCtx != null ? getFieldName(parentCtx, node) : null);
            obj.putNull("semantic");
            obj.set("children", mapper.createArrayNode());

        } else {
            ParserRuleContext ctx = (ParserRuleContext) node;
            Token start = ctx.start;
            Token stop = ctx.stop;

            int startByte = (start != null) ? byteOffset(start.getLine(), start.getCharPositionInLine()) : 0;
            int endByte = (stop != null)
                ? byteOffset(stop.getLine(), stop.getCharPositionInLine()) + stop.getText().length()
                : startByte;

            obj.put("type", getRuleName(ctx));
            obj.put("is_named", true);
            obj.set("start_point", start != null
                ? pointNode(start.getLine() - 1, start.getCharPositionInLine())
                : pointNode(0, 0));
            obj.set("end_point", stop != null
                ? pointNode(stop.getLine() - 1, stop.getCharPositionInLine() + stop.getText().length())
                : pointNode(0, 0));
            obj.put("start_byte", startByte);
            obj.put("end_byte", endByte);
            obj.put("field_name", parentCtx != null ? getFieldName(parentCtx, node) : null);
            obj.set("semantic", buildSemantic(ctx));

            ArrayNode children = mapper.createArrayNode();
            for (int i = 0; i < ctx.getChildCount(); i++) {
                children.add(serialize(ctx.getChild(i), ctx));
            }
            obj.set("children", children);
        }

        return obj;
    }

    private ArrayNode pointNode(int row, int col) {
        return mapper.createArrayNode().add(row).add(col);
    }

    private ObjectNode buildSemantic(ParserRuleContext ctx) {
        ASGElement element = registry.getASGElement(ctx);
        if (element == null) return null;

        ObjectNode sem = mapper.createObjectNode();

        if (element instanceof Function f) {
            sem.put("kind", "function");
            sem.put("name", f.getName());
            sem.put("visibility", f.getVisibility() != null ? f.getVisibility().name() : null);
            sem.put("return_type", f.getType() != null ? f.getType().getName() : null);

        } else if (element instanceof Sub s) {
            sem.put("kind", "sub");
            sem.put("name", s.getName());
            sem.put("visibility", s.getVisibility() != null ? s.getVisibility().name() : null);
            sem.putNull("return_type");

        } else if (element instanceof Module m) {
            sem.put("kind", "module");
            sem.put("name", m.getName());
            sem.putNull("visibility");
            sem.putNull("return_type");

        } else if (element instanceof Variable v) {
            sem.put("kind", "variable");
            sem.put("name", v.getName());
            sem.put("visibility", v.getVisibility() != null ? v.getVisibility().name() : null);
            sem.put("return_type", v.getType() != null ? v.getType().getName() : null);

        } else if (element instanceof NamedElement ne) {
            sem.put("kind", "element");
            sem.put("name", ne.getName());
            sem.putNull("visibility");
            sem.putNull("return_type");

        } else {
            return null;
        }

        return sem;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
mvn test -Dtest=ASTJsonSerializerTest -q
```

Expected: `Tests run: 5, Failures: 0, Errors: 0`.

- [ ] **Step 5: Commit**

```bash
git add src/main/java/io/proleap/vb6/cli/ASTJsonSerializer.java \
        src/test/java/io/proleap/vb6/cli/ASTJsonSerializerTest.java
git commit -m "feat: add ASTJsonSerializer for CST+ASG to JSON"
```

---

## Task 3: Implement VbParserCLI

**Files:**
- Create: `src/main/java/io/proleap/vb6/cli/VbParserCLI.java`
- Create: `src/test/java/io/proleap/vb6/cli/VbParserCLITest.java`

- [ ] **Step 1: Write the failing test**

Create `src/test/java/io/proleap/vb6/cli/VbParserCLITest.java`:

```java
package io.proleap.vb6.cli;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

import static org.junit.Assert.*;

public class VbParserCLITest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    private static final String HELLO_WORLD =
        "Private Sub Command1_Click ()\n" +
        "   Text1.Text = \"Hello, world!\"\n" +
        "End Sub\n";

    @Test
    public void fileArgProducesJsonWithModuleRoot() throws Exception {
        File bas = tmp.newFile("HelloWorld.bas");
        Files.writeString(bas.toPath(), HELLO_WORLD, StandardCharsets.UTF_8);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        System.setOut(new PrintStream(out));
        VbParserCLI.main(new String[]{"--file", bas.getAbsolutePath()});
        System.setOut(System.out);

        JsonNode root = new ObjectMapper().readTree(out.toString(StandardCharsets.UTF_8));
        assertEquals("module", root.get("type").asText());
    }

    @Test
    public void codeArgWithModuleNameProducesJson() throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        System.setOut(new PrintStream(out));
        VbParserCLI.main(new String[]{"--code", HELLO_WORLD, "--module-name", "MyMod"});
        System.setOut(System.out);

        JsonNode root = new ObjectMapper().readTree(out.toString(StandardCharsets.UTF_8));
        assertEquals("module", root.get("type").asText());
    }

    @Test
    public void invalidCodeExitsWithNonZeroAndPrintsNothing() throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();
        System.setOut(new PrintStream(out));
        System.setErr(new PrintStream(err));
        try {
            VbParserCLI.main(new String[]{"--code", "@@@@INVALID@@@@"});
        } catch (SystemExitException e) {
            assertEquals(1, e.status);
        } finally {
            System.setOut(System.out);
            System.setErr(System.err);
        }
        // stdout should be empty on error
        assertEquals("", out.toString(StandardCharsets.UTF_8).trim());
    }
}
```

Also create the `SystemExitException` helper used in the test. Add a nested class inside `VbParserCLITest`:

```java
    static class SystemExitException extends RuntimeException {
        final int status;
        SystemExitException(int status) { this.status = status; }
    }
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
mvn test -Dtest=VbParserCLITest -q 2>&1 | tail -5
```

Expected: compilation error — `VbParserCLI` not found.

- [ ] **Step 3: Create VbParserCLI.java**

Create `src/main/java/io/proleap/vb6/cli/VbParserCLI.java`:

```java
package io.proleap.vb6.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.proleap.vb6.asg.metamodel.Module;
import io.proleap.vb6.asg.metamodel.Program;
import io.proleap.vb6.asg.params.VbParserParams;
import io.proleap.vb6.asg.params.impl.VbParserParamsImpl;
import io.proleap.vb6.asg.runner.impl.VbParserRunnerImpl;
import org.antlr.v4.runtime.ParserRuleContext;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public class VbParserCLI {

    public static void main(String[] args) throws Exception {
        String filePath = null;
        String code = null;
        String moduleName = null;

        for (int i = 0; i < args.length - 1; i++) {
            switch (args[i]) {
                case "--file"        -> filePath   = args[++i];
                case "--code"        -> code       = args[++i];
                case "--module-name" -> moduleName = args[++i];
            }
        }

        try {
            if (filePath != null) {
                code = Files.readString(Path.of(filePath), StandardCharsets.UTF_8);
                if (moduleName == null) {
                    String fname = Path.of(filePath).getFileName().toString();
                    int dot = fname.lastIndexOf('.');
                    moduleName = dot > 0 ? fname.substring(0, dot) : fname;
                }
            }
            if (code == null) {
                System.err.println("Usage: vb6parser (--file <path> | --code <source>) [--module-name <name>]");
                System.exit(1);
                return;
            }
            if (moduleName == null) moduleName = "Module";

            VbParserParams params = new VbParserParamsImpl();
            Program program = new VbParserRunnerImpl().analyzeCode(code, moduleName, params);
            Module module = program.getModules().get(0);

            // Modules are not auto-registered in ASGElementRegistry; register manually
            // so ASTJsonSerializer can emit semantic info for the module root node.
            program.getASGElementRegistry().addASGElement(module);

            ASTJsonSerializer serializer = new ASTJsonSerializer(program.getASGElementRegistry(), code);
            Object root = serializer.serialize((ParserRuleContext) module.getCtx(), null);

            System.out.println(new ObjectMapper().writeValueAsString(root));

        } catch (Exception e) {
            System.err.println("Parse error: " + e.getMessage());
            System.exit(1);
        }
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
mvn test -Dtest=VbParserCLITest,ASTJsonSerializerTest -q
```

Expected: `Tests run: 8, Failures: 0, Errors: 0` (or similar count — all pass).

Note: the `invalidCodeExitsWithNonZeroAndPrintsNothing` test may require adjusting if the test catches `System.exit` via SecurityManager. If it fails, simplify: call `VbParserCLI.main(...)` in a try/catch for `Exception` and verify no JSON was written to stdout.

- [ ] **Step 5: Commit**

```bash
git add src/main/java/io/proleap/vb6/cli/VbParserCLI.java \
        src/test/java/io/proleap/vb6/cli/VbParserCLITest.java
git commit -m "feat: add VbParserCLI entry point"
```

---

## Task 4: Build fat jar and scaffold Python project

**Files:**
- Create: `vb6-parser-python/` directory tree
- Create: `vb6-parser-python/resources/vb6parser.jar` (copied from build)

- [ ] **Step 1: Build fat jar**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
mvn package -DskipTests -q
ls -lh target/vb6parser.jar
```

Expected: `target/vb6parser.jar` exists, size > 5 MB.

- [ ] **Step 2: Scaffold Python project directories**

```bash
mkdir -p /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python/vb6_parser
mkdir -p /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python/resources
mkdir -p /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python/tests
```

- [ ] **Step 3: Copy jar to resources**

```bash
cp /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/target/vb6parser.jar \
   /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python/resources/vb6parser.jar
```

- [ ] **Step 4: Create pyproject.toml**

Create `vb6-parser-python/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "vb6-parser"
version = "0.1.0"
requires-python = ">=3.10"
description = "tree-sitter-compatible API for VB6, backed by proleap-vb6-parser"

[tool.setuptools.packages.find]
where = ["."]
include = ["vb6_parser*"]

[tool.setuptools.package-data]
vb6_parser = ["../resources/*.jar"]
```

- [ ] **Step 5: Create tests/conftest.py with VB6 fixtures**

Create `vb6-parser-python/tests/conftest.py`:

```python
import pytest
from pathlib import Path

HELLO_WORLD = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"

MODULE_WITH_FUNCTION = b"""Public Function Add(x As Integer, y As Integer) As Integer
    Add = x + y
End Function

Private Sub Greet()
    MsgBox "Hello"
End Sub
"""

@pytest.fixture
def hello_world_source():
    return HELLO_WORLD

@pytest.fixture
def module_with_function_source():
    return MODULE_WITH_FUNCTION
```

- [ ] **Step 6: Commit**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
git add vb6-parser-python/
git commit -m "build: scaffold Python project and copy fat jar"
```

---

## Task 5: Python — _errors.py

**Files:**
- Create: `vb6-parser-python/vb6_parser/_errors.py`

- [ ] **Step 1: Write failing test**

Create `vb6-parser-python/tests/test_errors.py`:

```python
from vb6_parser._errors import ParseError, VbRuntimeError, InternalError

def test_parse_error_is_exception():
    e = ParseError("bad syntax", stderr="details here")
    assert isinstance(e, Exception)
    assert "bad syntax" in str(e)
    assert e.stderr == "details here"

def test_runtime_error_carries_hint():
    e = VbRuntimeError("JRE not found. Install Java 17+.")
    assert "Java" in str(e)

def test_internal_error():
    e = InternalError("json decode failed")
    assert isinstance(e, Exception)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/test_errors.py -q 2>&1 | tail -5
```

Expected: `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Create _errors.py**

Create `vb6-parser-python/vb6_parser/_errors.py`:

```python
class ParseError(Exception):
    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr

class VbRuntimeError(Exception):
    pass

class InternalError(Exception):
    pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/test_errors.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
git add vb6-parser-python/vb6_parser/_errors.py vb6-parser-python/tests/test_errors.py
git commit -m "feat: add Python error types"
```

---

## Task 6: Python — _node.py

**Files:**
- Create: `vb6-parser-python/vb6_parser/_node.py`

- [ ] **Step 1: Write failing tests**

Create `vb6-parser-python/tests/test_node.py`:

```python
import json
from vb6_parser._node import Node

SAMPLE_JSON = {
    "type": "module",
    "is_named": True,
    "start_point": [0, 0],
    "end_point": [3, 0],
    "start_byte": 0,
    "end_byte": 68,
    "field_name": None,
    "semantic": None,
    "children": [
        {
            "type": "subStmt",
            "is_named": True,
            "start_point": [0, 0],
            "end_point": [2, 7],
            "start_byte": 0,
            "end_byte": 68,
            "field_name": None,
            "semantic": {"kind": "sub", "name": "Command1_Click", "visibility": "PRIVATE", "return_type": None},
            "children": [
                {
                    "type": "Command1_Click",
                    "is_named": False,
                    "start_point": [0, 12],
                    "end_point": [0, 26],
                    "start_byte": 12,
                    "end_byte": 26,
                    "field_name": "name",
                    "semantic": None,
                    "children": []
                }
            ]
        }
    ]
}

SOURCE = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"

def make_root():
    return Node(SAMPLE_JSON, SOURCE)

def test_type():
    assert make_root().type == "module"

def test_is_named():
    assert make_root().is_named is True

def test_start_point():
    assert make_root().start_point == (0, 0)

def test_end_point():
    assert make_root().end_point == (3, 0)

def test_start_byte():
    assert make_root().start_byte == 0

def test_end_byte():
    assert make_root().end_byte == 68

def test_text():
    assert make_root().text == SOURCE[0:68]

def test_children_count():
    root = make_root()
    assert root.child_count == 1

def test_named_children():
    root = make_root()
    assert len(root.named_children) == 1
    assert root.named_children[0].type == "subStmt"

def test_named_child_count():
    assert make_root().named_child_count == 1

def test_parent_is_none_for_root():
    assert make_root().parent is None

def test_parent_set_on_children():
    root = make_root()
    child = root.children[0]
    assert child.parent is root

def test_semantic_is_none_for_root():
    assert make_root().semantic is None

def test_semantic_on_sub_stmt():
    root = make_root()
    sub = root.children[0]
    assert sub.semantic["kind"] == "sub"
    assert sub.semantic["name"] == "Command1_Click"

def test_descendants_of_type():
    root = make_root()
    subs = root.descendants_of_type("subStmt")
    assert len(subs) == 1
    assert subs[0].type == "subStmt"

def test_descendants_of_type_multiple():
    root = make_root()
    results = root.descendants_of_type("subStmt", "module")
    types = {n.type for n in results}
    assert "subStmt" in types

def test_child_by_field_name():
    root = make_root()
    sub = root.children[0]
    name_node = sub.child_by_field_name("name")
    assert name_node is not None
    assert name_node.type == "Command1_Click"

def test_child_by_field_name_missing():
    root = make_root()
    assert root.child_by_field_name("nonexistent") is None

def test_children_by_field_name():
    root = make_root()
    sub = root.children[0]
    results = sub.children_by_field_name("name")
    assert len(results) == 1

def test_walk_returns_cursor():
    from vb6_parser._cursor import TreeCursor
    cursor = make_root().walk()
    assert isinstance(cursor, TreeCursor)
    assert cursor.node.type == "module"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/test_node.py -q 2>&1 | tail -5
```

Expected: `ImportError`.

- [ ] **Step 3: Create _node.py**

Create `vb6-parser-python/vb6_parser/_node.py`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vb6_parser._cursor import TreeCursor


class Node:
    __slots__ = ("_data", "_source", "_parent", "_children")

    def __init__(self, data: dict, source: bytes, parent: "Node | None" = None):
        self._data = data
        self._source = source
        self._parent = parent
        self._children: list[Node] | None = None

    def _build_children(self) -> list["Node"]:
        if self._children is None:
            self._children = [
                Node(c, self._source, parent=self)
                for c in self._data.get("children", [])
            ]
        return self._children

    @property
    def type(self) -> str:
        return self._data["type"]

    @property
    def is_named(self) -> bool:
        return bool(self._data["is_named"])

    @property
    def start_point(self) -> tuple[int, int]:
        p = self._data["start_point"]
        return (p[0], p[1])

    @property
    def end_point(self) -> tuple[int, int]:
        p = self._data["end_point"]
        return (p[0], p[1])

    @property
    def start_byte(self) -> int:
        return self._data["start_byte"]

    @property
    def end_byte(self) -> int:
        return self._data["end_byte"]

    @property
    def text(self) -> bytes:
        return self._source[self.start_byte:self.end_byte]

    @property
    def parent(self) -> "Node | None":
        return self._parent

    @property
    def children(self) -> list["Node"]:
        return self._build_children()

    @property
    def named_children(self) -> list["Node"]:
        return [c for c in self.children if c.is_named]

    @property
    def child_count(self) -> int:
        return len(self.children)

    @property
    def named_child_count(self) -> int:
        return len(self.named_children)

    @property
    def semantic(self) -> dict | None:
        return self._data.get("semantic") or None

    def child_by_field_name(self, name: str) -> "Node | None":
        for child in self.children:
            if child._data.get("field_name") == name:
                return child
        return None

    def children_by_field_name(self, name: str) -> list["Node"]:
        return [c for c in self.children if c._data.get("field_name") == name]

    def descendants_of_type(self, *types: str) -> list["Node"]:
        result: list[Node] = []
        type_set = set(types)
        self._collect_descendants(type_set, result)
        return result

    def _collect_descendants(self, types: set[str], acc: list["Node"]) -> None:
        for child in self.children:
            if child.type in types:
                acc.append(child)
            child._collect_descendants(types, acc)

    def walk(self) -> "TreeCursor":
        from vb6_parser._cursor import TreeCursor
        return TreeCursor(self)

    def __repr__(self) -> str:
        return f"<Node type={self.type!r} [{self.start_point}..{self.end_point}]>"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/test_node.py -q
```

Expected: all pass. If `test_walk_returns_cursor` fails with ImportError (cursor not yet created), skip it with `-k "not walk"` and revisit in Task 7.

- [ ] **Step 5: Commit**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
git add vb6-parser-python/vb6_parser/_node.py vb6-parser-python/tests/test_node.py
git commit -m "feat: implement Node class with tree-sitter API"
```

---

## Task 7: Python — _tree.py + _cursor.py

**Files:**
- Create: `vb6-parser-python/vb6_parser/_tree.py`
- Create: `vb6-parser-python/vb6_parser/_cursor.py`

- [ ] **Step 1: Write failing tests**

Create `vb6-parser-python/tests/test_cursor.py`:

```python
from vb6_parser._node import Node
from vb6_parser._tree import Tree
from vb6_parser._cursor import TreeCursor

SAMPLE_JSON = {
    "type": "module",
    "is_named": True,
    "start_point": [0, 0], "end_point": [3, 0],
    "start_byte": 0, "end_byte": 68,
    "field_name": None, "semantic": None,
    "children": [
        {
            "type": "subStmt",
            "is_named": True,
            "start_point": [0, 0], "end_point": [2, 7],
            "start_byte": 0, "end_byte": 68,
            "field_name": None,
            "semantic": {"kind": "sub", "name": "Command1_Click", "visibility": "PRIVATE", "return_type": None},
            "children": [
                {
                    "type": "Command1_Click",
                    "is_named": False,
                    "start_point": [0, 12], "end_point": [0, 26],
                    "start_byte": 12, "end_byte": 26,
                    "field_name": "name", "semantic": None, "children": []
                }
            ]
        }
    ]
}

SOURCE = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"


def make_tree():
    return Tree(Node(SAMPLE_JSON, SOURCE), SOURCE)


def test_tree_root_node_type():
    assert make_tree().root_node.type == "module"


def test_tree_source():
    assert make_tree().source == SOURCE


def test_cursor_initial_node():
    cursor = make_tree().root_node.walk()
    assert cursor.node.type == "module"


def test_cursor_goto_first_child():
    cursor = make_tree().root_node.walk()
    moved = cursor.goto_first_child()
    assert moved is True
    assert cursor.node.type == "subStmt"


def test_cursor_goto_first_child_leaf_returns_false():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()   # -> subStmt
    cursor.goto_first_child()   # -> Command1_Click (terminal, no children)
    moved = cursor.goto_first_child()
    assert moved is False


def test_cursor_goto_next_sibling():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()
    # subStmt is only child; no sibling
    moved = cursor.goto_next_sibling()
    assert moved is False


def test_cursor_goto_parent():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()
    moved = cursor.goto_parent()
    assert moved is True
    assert cursor.node.type == "module"


def test_cursor_goto_parent_at_root_returns_false():
    cursor = make_tree().root_node.walk()
    moved = cursor.goto_parent()
    assert moved is False


def test_cursor_current_field_name():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()    # subStmt — field_name None
    cursor.goto_first_child()    # Command1_Click — field_name "name"
    assert cursor.current_field_name == "name"


def test_cursor_reset():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()
    sub_node = cursor.node
    cursor.goto_first_child()
    cursor.reset(sub_node)
    assert cursor.node.type == "subStmt"


def test_full_traversal_visits_all_nodes():
    tree = make_tree()
    visited = []
    cursor = tree.root_node.walk()
    while True:
        visited.append(cursor.node.type)
        if cursor.goto_first_child():
            continue
        if cursor.goto_next_sibling():
            continue
        while cursor.goto_parent():
            if cursor.goto_next_sibling():
                break
        else:
            break
    assert "module" in visited
    assert "subStmt" in visited
    assert "Command1_Click" in visited
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/test_cursor.py -q 2>&1 | tail -5
```

Expected: `ImportError`.

- [ ] **Step 3: Create _cursor.py**

Create `vb6-parser-python/vb6_parser/_cursor.py`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vb6_parser._node import Node


class TreeCursor:
    __slots__ = ("_node",)

    def __init__(self, node: "Node"):
        self._node = node

    @property
    def node(self) -> "Node":
        return self._node

    @property
    def current_field_name(self) -> str | None:
        return self._node._data.get("field_name")

    def goto_first_child(self) -> bool:
        children = self._node.children
        if not children:
            return False
        self._node = children[0]
        return True

    def goto_next_sibling(self) -> bool:
        parent = self._node.parent
        if parent is None:
            return False
        siblings = parent.children
        idx = next((i for i, c in enumerate(siblings) if c is self._node), -1)
        if idx < 0 or idx + 1 >= len(siblings):
            return False
        self._node = siblings[idx + 1]
        return True

    def goto_parent(self) -> bool:
        if self._node.parent is None:
            return False
        self._node = self._node.parent
        return True

    def reset(self, node: "Node") -> None:
        self._node = node
```

- [ ] **Step 4: Create _tree.py**

Create `vb6-parser-python/vb6_parser/_tree.py`:

```python
from __future__ import annotations
from vb6_parser._node import Node


class Tree:
    __slots__ = ("_root", "_source")

    def __init__(self, root: Node, source: bytes):
        self._root = root
        self._source = source

    @property
    def root_node(self) -> Node:
        return self._root

    @property
    def source(self) -> bytes:
        return self._source

    def __repr__(self) -> str:
        return f"<Tree root={self._root.type!r}>"
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/test_cursor.py tests/test_node.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
git add vb6-parser-python/vb6_parser/_tree.py \
        vb6-parser-python/vb6_parser/_cursor.py \
        vb6-parser-python/tests/test_cursor.py
git commit -m "feat: add Tree and TreeCursor classes"
```

---

## Task 8: Python — _jar.py + _parser.py

**Files:**
- Create: `vb6-parser-python/vb6_parser/_jar.py`
- Create: `vb6-parser-python/vb6_parser/_parser.py`

- [ ] **Step 1: Write failing tests**

Create `vb6-parser-python/tests/test_basic.py`:

```python
import pytest
from vb6_parser._parser import Parser
from vb6_parser._tree import Tree
from vb6_parser._node import Node
from vb6_parser._errors import ParseError

HELLO_WORLD = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"

MODULE_WITH_FUNCTION = b"""Public Function Add(x As Integer, y As Integer) As Integer
    Add = x + y
End Function

Private Sub Greet()
    MsgBox "Hello"
End Sub
"""

def test_parse_returns_tree():
    tree = Parser().parse(HELLO_WORLD)
    assert isinstance(tree, Tree)

def test_root_node_is_module():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.type == "module"

def test_root_is_named():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.is_named is True

def test_start_point_zero():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.start_point == (0, 0)

def test_source_preserved():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.source == HELLO_WORLD

def test_find_sub_stmt():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    assert len(subs) >= 1

def test_find_function_and_sub():
    tree = Parser().parse(MODULE_WITH_FUNCTION)
    funcs = tree.root_node.descendants_of_type("functionStmt")
    subs = tree.root_node.descendants_of_type("subStmt")
    assert len(funcs) >= 1
    assert len(subs) >= 1

def test_parse_string_input():
    tree = Parser().parse("Private Sub Test()\nEnd Sub\n")
    assert tree.root_node.type == "module"

def test_parse_invalid_raises_parse_error():
    with pytest.raises(ParseError):
        Parser().parse("@@@@NOT_VALID_VB6@@@@")

def test_child_count_positive():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.child_count > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/test_basic.py -q 2>&1 | tail -5
```

Expected: `ImportError`.

- [ ] **Step 3: Create _jar.py**

Create `vb6-parser-python/vb6_parser/_jar.py`:

```python
from pathlib import Path

_RESOURCES = Path(__file__).parent.parent / "resources"

def find_jar() -> Path:
    jar = _RESOURCES / "vb6parser.jar"
    if jar.exists():
        return jar
    raise FileNotFoundError(
        f"vb6parser.jar not found at {jar}. "
        "Run `mvn package -DskipTests` in proleap-vb6-parser/ and copy target/vb6parser.jar to resources/."
    )
```

- [ ] **Step 4: Create _parser.py**

Create `vb6-parser-python/vb6_parser/_parser.py`:

```python
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from vb6_parser._errors import InternalError, ParseError, VbRuntimeError
from vb6_parser._jar import find_jar
from vb6_parser._node import Node
from vb6_parser._tree import Tree


class Parser:
    def __init__(self, jar_path: str | Path | None = None):
        self._jar = Path(jar_path) if jar_path else find_jar()

    def parse(self, code: str | bytes, module_name: str = "Module") -> Tree:
        if isinstance(code, str):
            source = code.encode("utf-8")
        else:
            source = code

        with tempfile.NamedTemporaryFile(suffix=".bas", delete=False) as f:
            f.write(source)
            tmp_path = f.name

        try:
            return self._run(tmp_path, source, module_name)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def parse_file(self, path: str | Path) -> Tree:
        p = Path(path)
        source = p.read_bytes()
        return self._run(str(p), source, p.stem)

    def _run(self, file_path: str, source: bytes, module_name: str) -> Tree:
        try:
            result = subprocess.run(
                ["java", "-jar", str(self._jar),
                 "--file", file_path,
                 "--module-name", module_name],
                capture_output=True,
                timeout=30,
            )
        except FileNotFoundError:
            raise VbRuntimeError(
                "java not found in PATH. Install Java 17+ and ensure it is on your PATH."
            )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise ParseError(f"VB6 parse failed for module '{module_name}'", stderr=stderr)

        stdout = result.stdout.decode("utf-8", errors="replace")
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise InternalError(f"JSON decode failed: {e}\nOutput was: {stdout[:200]}")

        root = Node(data, source)
        return Tree(root, source)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/test_basic.py -q
```

Expected: all pass. If `test_parse_invalid_raises_parse_error` fails because proleap ignores the syntax error, replace `"@@@@NOT_VALID_VB6@@@@"` with a snippet that triggers a known ANTLR parse error, or check the VbParserParams `ignoreSyntaxErrors` default.

- [ ] **Step 6: Commit**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
git add vb6-parser-python/vb6_parser/_jar.py \
        vb6-parser-python/vb6_parser/_parser.py \
        vb6-parser-python/tests/test_basic.py
git commit -m "feat: add Parser class with subprocess+JSON bridge"
```

---

## Task 9: Python — test_semantic.py + __init__.py

**Files:**
- Create: `vb6-parser-python/tests/test_semantic.py`
- Create: `vb6-parser-python/vb6_parser/__init__.py`

- [ ] **Step 1: Write semantic tests**

Create `vb6-parser-python/tests/test_semantic.py`:

```python
from vb6_parser import Parser

MODULE_WITH_FUNCTION = b"""Public Function Add(x As Integer, y As Integer) As Integer
    Add = x + y
End Function

Private Sub Greet()
    MsgBox "Hello"
End Sub
"""

HELLO_WORLD = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"


def test_sub_semantic_kind():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    assert len(subs) >= 1
    sem = subs[0].semantic
    assert sem is not None
    assert sem["kind"] == "sub"


def test_sub_semantic_name():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    assert subs[0].semantic["name"] == "Command1_Click"


def test_sub_semantic_visibility():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    assert subs[0].semantic["visibility"] == "PRIVATE"


def test_function_semantic_kind():
    tree = Parser().parse(MODULE_WITH_FUNCTION)
    funcs = tree.root_node.descendants_of_type("functionStmt")
    assert len(funcs) >= 1
    sem = funcs[0].semantic
    assert sem is not None
    assert sem["kind"] == "function"


def test_function_semantic_name():
    tree = Parser().parse(MODULE_WITH_FUNCTION)
    funcs = tree.root_node.descendants_of_type("functionStmt")
    assert funcs[0].semantic["name"] == "Add"


def test_function_semantic_visibility():
    tree = Parser().parse(MODULE_WITH_FUNCTION)
    funcs = tree.root_node.descendants_of_type("functionStmt")
    assert funcs[0].semantic["visibility"] == "PUBLIC"


def test_module_semantic():
    tree = Parser().parse(HELLO_WORLD, module_name="TestModule")
    root = tree.root_node
    # module node itself should have semantic kind=module
    sem = root.semantic
    assert sem is not None
    assert sem["kind"] == "module"
    assert sem["name"] == "TestModule"


def test_child_by_field_name_on_sub():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    name_node = subs[0].child_by_field_name("name")
    assert name_node is not None
    assert b"Command1_Click" in name_node.text


def test_nodes_without_semantic_return_none():
    tree = Parser().parse(HELLO_WORLD)
    # terminal nodes (anonymous) have no semantic
    terminals = [n for n in tree.root_node.descendants_of_type("Sub")]
    # "Sub" keyword node is anonymous (is_named=False) — just check some non-proc node
    all_nodes = _all_nodes(tree.root_node)
    no_sem = [n for n in all_nodes if n.semantic is None]
    assert len(no_sem) > 0  # many nodes have no semantic


def _all_nodes(node):
    yield node
    for child in node.children:
        yield from _all_nodes(child)
```

- [ ] **Step 2: Create __init__.py**

Create `vb6-parser-python/vb6_parser/__init__.py`:

```python
from vb6_parser._parser import Parser
from vb6_parser._tree import Tree
from vb6_parser._node import Node
from vb6_parser._cursor import TreeCursor
from vb6_parser._errors import ParseError, VbRuntimeError, InternalError

__all__ = ["Parser", "Tree", "Node", "TreeCursor", "ParseError", "VbRuntimeError", "InternalError"]
```

- [ ] **Step 3: Run all tests**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/ -q
```

Expected: all pass. Any failures in `test_semantic.py` are likely due to `module.getCtx()` not matching `ASGElementRegistry` key — debug by printing the registry keys vs ctx class in Java.

- [ ] **Step 4: Commit**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
git add vb6-parser-python/vb6_parser/__init__.py \
        vb6-parser-python/tests/test_semantic.py
git commit -m "feat: wire up __init__.py and add semantic tests"
```

---

## Task 10: Final verification

- [ ] **Step 1: Run full test suite (Java)**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
mvn test -q
```

Expected: all existing + new tests pass. Zero failures.

- [ ] **Step 2: Run full test suite (Python)**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Smoke-test end-to-end from CLI**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
echo 'Private Sub Hello()\n    MsgBox "hi"\nEnd Sub' > /tmp/smoke.bas
java -jar target/vb6parser.jar --file /tmp/smoke.bas | python3 -m json.tool | head -20
```

Expected: pretty-printed JSON with `"type": "module"` at root.

- [ ] **Step 4: Smoke-test from Python**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser/vb6-parser-python
python3 - <<'EOF'
from vb6_parser import Parser
tree = Parser().parse(b"Private Sub Hello()\n    MsgBox \"hi\"\nEnd Sub\n")
for proc in tree.root_node.descendants_of_type("subStmt"):
    name = proc.child_by_field_name("name")
    print(f"proc: {name.text.decode()!r}  visibility: {proc.semantic['visibility']}")
EOF
```

Expected output: `proc: 'Hello'  visibility: 'PRIVATE'`

- [ ] **Step 5: Final commit**

```bash
cd /Users/asteroid/Code/CodeAnalyzer/proleap-vb6-parser
git add .
git commit -m "feat: complete vb6 tree-sitter adapter (Java CLI + Python library)"
```
