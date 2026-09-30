pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement {
    repositories {
        exclusiveContent {
            forRepository { maven { url = uri(providers.gradleProperty("ftmsRepository").get()) } }
            filter { includeModule("io.github.deancochran", "ftms") }
        }
        google()
        mavenCentral()
    }
}
rootProject.name = "ftms-android-consumer"
