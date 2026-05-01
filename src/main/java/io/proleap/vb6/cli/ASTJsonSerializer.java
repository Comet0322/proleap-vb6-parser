package io.proleap.vb6.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.proleap.vb6.VisualBasic6Parser;
import io.proleap.vb6.asg.metamodel.Arg;
import io.proleap.vb6.asg.metamodel.ASGElement;
import io.proleap.vb6.asg.metamodel.Module;
import io.proleap.vb6.asg.metamodel.NamedElement;
import io.proleap.vb6.asg.metamodel.Procedure;
import io.proleap.vb6.asg.metamodel.Scope;
import io.proleap.vb6.asg.metamodel.Variable;
import io.proleap.vb6.asg.metamodel.call.Call;
import io.proleap.vb6.asg.metamodel.registry.ASGElementRegistry;
import io.proleap.vb6.asg.metamodel.statement.function.Function;
import io.proleap.vb6.asg.metamodel.statement.sub.Sub;
import io.proleap.vb6.asg.metamodel.statement.property.get.PropertyGet;
import io.proleap.vb6.asg.metamodel.statement.property.let.PropertyLet;
import io.proleap.vb6.asg.metamodel.statement.property.set.PropertySet;
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
        String name = simple.endsWith("Context") ? simple.substring(0, simple.length() - 7) : simple;
        if (name.isEmpty()) return name;
        return Character.toLowerCase(name.charAt(0)) + name.substring(1);
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

    // Params: [{name, type, is_optional}]
    private ArrayNode buildParams(Procedure proc) {
        ArrayNode params = mapper.createArrayNode();
        for (Arg arg : proc.getArgsList()) {
            ObjectNode p = mapper.createObjectNode();
            p.put("name", arg.getName());
            p.put("type", arg.getType() != null ? arg.getType().getName() : null);
            p.put("is_optional", arg.isOptional());
            params.add(p);
        }
        return params;
    }

    // Callers: [{name, line}] — each entry is a call-site that invokes this procedure.
    // proc.getCalls() returns incoming calls (SubCall/FunctionCall objects pointing TO this proc),
    // not outgoing calls. scope of each call is the containing procedure or module.
    private ArrayNode buildCallers(Procedure proc) {
        ArrayNode callers = mapper.createArrayNode();
        for (Call c : proc.getCalls()) {
            Scope scope = c.getScope();
            String callerName = (scope instanceof NamedElement ne) ? ne.getName() : null;
            int line = (c.getCtx() != null && c.getCtx().start != null)
                ? c.getCtx().start.getLine() - 1  // 0-indexed
                : -1;
            ObjectNode entry = mapper.createObjectNode();
            entry.put("name", callerName);
            entry.put("line", line);
            callers.add(entry);
        }
        return callers;
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
            sem.set("params", buildParams(f));
            sem.set("callers", buildCallers(f));

        } else if (element instanceof Sub s) {
            sem.put("kind", "sub");
            sem.put("name", s.getName());
            sem.put("visibility", s.getVisibility() != null ? s.getVisibility().name() : null);
            sem.putNull("return_type");
            sem.set("params", buildParams(s));
            sem.set("callers", buildCallers(s));

        } else if (element instanceof PropertyGet pg) {
            sem.put("kind", "propertyGet");
            sem.put("name", pg.getName());
            sem.put("visibility", pg.getVisibility() != null ? pg.getVisibility().name() : null);
            sem.put("return_type", pg.getType() != null ? pg.getType().getName() : null);
            sem.set("params", buildParams(pg));
            sem.set("callers", buildCallers(pg));

        } else if (element instanceof PropertyLet pl) {
            sem.put("kind", "propertyLet");
            sem.put("name", pl.getName());
            sem.put("visibility", pl.getVisibility() != null ? pl.getVisibility().name() : null);
            sem.putNull("return_type");
            sem.set("params", buildParams(pl));
            sem.set("callers", buildCallers(pl));

        } else if (element instanceof PropertySet ps) {
            sem.put("kind", "propertySet");
            sem.put("name", ps.getName());
            sem.put("visibility", ps.getVisibility() != null ? ps.getVisibility().name() : null);
            sem.putNull("return_type");
            sem.set("params", buildParams(ps));
            sem.set("callers", buildCallers(ps));

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
