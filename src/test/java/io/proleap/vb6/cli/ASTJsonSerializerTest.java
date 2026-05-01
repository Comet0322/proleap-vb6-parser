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
