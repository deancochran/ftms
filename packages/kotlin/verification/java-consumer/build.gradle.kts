plugins { application }
repositories {
    exclusiveContent {
        forRepository { maven { url = uri(providers.gradleProperty("ftmsRepository").get()) } }
        filter { includeModule("io.github.deancochran", "ftms") }
    }
    mavenCentral()
}
dependencies { implementation("io.github.deancochran:ftms:0.1.0") }
java { toolchain { languageVersion.set(JavaLanguageVersion.of(17)) } }
application { mainClass.set("example.Consumer") }
