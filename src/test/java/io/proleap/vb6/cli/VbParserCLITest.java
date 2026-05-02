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
import java.nio.file.Path;

import static org.junit.Assert.*;

public class VbParserCLITest {

    // Use project target directory as temp parent to avoid sandbox restrictions on /var/folders
    private static final File TEMP_PARENT = new File(
        System.getProperty("project.build.directory",
            Path.of(System.getProperty("user.dir"), "target").toString())
    );

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder(TEMP_PARENT);

    private static final String HELLO_WORLD =
        "Private Sub Command1_Click ()\n" +
        "   Text1.Text = \"Hello, world!\"\n" +
        "End Sub\n";

    @Test
    public void fileArgProducesJsonWithModuleRoot() throws Exception {
        File bas = tmp.newFile("HelloWorld.bas");
        Files.writeString(bas.toPath(), HELLO_WORLD, StandardCharsets.UTF_8);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        PrintStream originalOut = System.out;
        System.setOut(new PrintStream(out));
        try {
            VbParserCLI.main(new String[]{"--file", bas.getAbsolutePath()});
        } finally {
            System.setOut(originalOut);
        }

        JsonNode root = new ObjectMapper().readTree(out.toString(StandardCharsets.UTF_8));
        assertEquals("module", root.get("type").asText());
    }

    @Test
    public void codeArgWithModuleNameProducesJson() throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        PrintStream originalOut = System.out;
        System.setOut(new PrintStream(out));
        try {
            VbParserCLI.main(new String[]{"--code", HELLO_WORLD, "--module-name", "MyMod"});
        } finally {
            System.setOut(originalOut);
        }

        JsonNode root = new ObjectMapper().readTree(out.toString(StandardCharsets.UTF_8));
        assertEquals("module", root.get("type").asText());
    }

    @Test
    public void moduleSemanticIsPresentInOutput() throws Exception {
        File bas = tmp.newFile("TestModule.bas");
        Files.writeString(bas.toPath(), HELLO_WORLD, StandardCharsets.UTF_8);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        PrintStream originalOut = System.out;
        System.setOut(new PrintStream(out));
        try {
            VbParserCLI.main(new String[]{"--file", bas.getAbsolutePath()});
        } finally {
            System.setOut(originalOut);
        }

        JsonNode root = new ObjectMapper().readTree(out.toString(StandardCharsets.UTF_8));
        assertFalse("module node should have semantic", root.get("semantic").isNull());
        assertEquals("module", root.get("semantic").get("kind").asText());
        assertEquals("TestModule", root.get("semantic").get("name").asText());
    }
}
