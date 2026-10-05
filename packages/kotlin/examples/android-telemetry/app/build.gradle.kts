plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }

android {
    namespace = "io.github.deancochran.ftms.example.telemetry"
    compileSdk = 35
    defaultConfig {
        applicationId = "io.github.deancochran.ftms.example.telemetry"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("io.github.deancochran:ftms:0.2.0")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:core:1.6.1")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
