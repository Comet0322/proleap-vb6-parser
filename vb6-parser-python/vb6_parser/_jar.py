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
