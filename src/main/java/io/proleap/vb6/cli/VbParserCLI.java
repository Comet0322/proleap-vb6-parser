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

            // Ensure the module is registered in the ASGElementRegistry
            // so ASTJsonSerializer can emit semantic info for the module root node.
            // Guard against double-registration (the library may already register it).
            if (program.getASGElementRegistry().getASGElement(module.getCtx()) == null) {
                program.getASGElementRegistry().addASGElement(module);
            }

            ASTJsonSerializer serializer = new ASTJsonSerializer(program.getASGElementRegistry(), code);
            Object root = serializer.serialize((ParserRuleContext) module.getCtx(), null);

            System.out.println(new ObjectMapper().writeValueAsString(root));

        } catch (Exception e) {
            System.err.println("Parse error: " + e.getMessage());
            System.exit(1);
        }
    }
}
