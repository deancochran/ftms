plugins { id("com.android.application") version "8.10.1" }
android {
    namespace = "example.ftms"
    compileSdk = 35
    defaultConfig {
        applicationId = "example.ftms"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
dependencies { implementation("io.github.deancochran:ftms:${providers.gradleProperty("ftmsVersion").orElse("0.1.0").get()}") }
