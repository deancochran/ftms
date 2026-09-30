plugins {
    kotlin("jvm") version "2.2.0"
    application
}
repositories {
    exclusiveContent {
        forRepository { maven { url = uri(providers.gradleProperty("ftmsRepository").get()) } }
        filter { includeModule("io.github.deancochran", "ftms") }
    }
    mavenCentral()
}
dependencies { implementation("io.github.deancochran:ftms:0.1.0") }
kotlin { jvmToolchain(17) }
application { mainClass.set("example.ConsumerKt") }
