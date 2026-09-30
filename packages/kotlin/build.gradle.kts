plugins {
  kotlin("jvm") version "2.2.0"
  `java-library`
  `maven-publish`
  id("org.jetbrains.dokka") version "2.0.0"
  id("org.jetbrains.kotlinx.binary-compatibility-validator") version "0.18.1"
}

group = "io.github.deancochran"
version = "0.1.0"

kotlin { jvmToolchain(17); explicitApi() }

repositories { mavenCentral() }

dependencies {
  testImplementation(kotlin("test"))
  testImplementation("org.junit.jupiter:junit-jupiter:5.11.4")
  testImplementation("com.google.code.gson:gson:2.13.1")
  testImplementation("com.networknt:json-schema-validator:1.5.8")
  testRuntimeOnly("org.junit.platform:junit-platform-launcher:1.11.4")
}

tasks.test { useJUnitPlatform() }

java { withSourcesJar() }

val documentationJar by tasks.registering(Jar::class) {
  archiveClassifier.set("javadoc")
  from(tasks.named("dokkaGeneratePublicationHtml"))
}
tasks.withType<AbstractArchiveTask>().configureEach {
  isPreserveFileTimestamps = false
  isReproducibleFileOrder = true
}
tasks.withType<Jar>().configureEach { from("../../LICENSE") { into("META-INF") } }

dependencyLocking { lockAllConfigurations() }

publishing {
  publications {
    create<MavenPublication>("mavenJava") {
      from(components["java"])
      artifactId = "ftms"
      artifact(documentationJar)
      pom {
        name.set("FTMS Kotlin")
        description.set("Transport-independent Kotlin/JVM Fitness Machine Service protocol codecs")
        url.set("https://github.com/deancochran/ftms")
        licenses { license { name.set("MIT License"); url.set("https://opensource.org/licenses/MIT") } }
        developers { developer { id.set("deancochran"); name.set("Dean Cochran") } }
        scm {
          url.set("https://github.com/deancochran/ftms")
          connection.set("scm:git:https://github.com/deancochran/ftms.git")
          developerConnection.set("scm:git:ssh://git@github.com/deancochran/ftms.git")
        }
      }
    }
  }
  repositories { maven { name = "localVerification"; url = uri(layout.buildDirectory.dir("local-maven")) } }
}
