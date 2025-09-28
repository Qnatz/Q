# Deployment Plan for Expense Tracker Android App

This document outlines the steps to build and deploy the Expense Tracker Android application to a device or emulator, including instructions for creating a signed APK for distribution.

## 1. Prerequisites

*   **Android Studio:**  Installed and configured with the Android SDK.
*   **Android Device or Emulator:**  A physical Android device or an emulator configured in Android Studio.
*   **Java Development Kit (JDK):** Ensure JDK is installed and correctly configured.

## 2. Building the Application

1.  **Open Project in Android Studio:** Open the Expense Tracker project in Android Studio.
2.  **Clean Project:**  Navigate to `Build > Clean Project`. This removes any previously built files and ensures a fresh build.
3.  **Rebuild Project:** Navigate to `Build > Rebuild Project`. This compiles the source code and resources.
4.  **Build APK (Debug):** Navigate to `Build > Build Bundle(s)/APK(s) > Build APK(s)`. This creates a debug APK file.  The debug APK is suitable for testing on emulators or developer devices.  The location of the APK is shown in the "Build" tab at the bottom of Android Studio.  It typically is in `app/build/outputs/apk/debug/app-debug.apk`

## 3. Deploying to Device/Emulator (Debug APK)

1.  **Connect Device/Start Emulator:** Connect your Android device to your computer via USB or start your emulator in Android Studio.
2.  **Enable USB Debugging (Device):** On your Android device, enable USB debugging in the developer options. (Settings -> About Phone -> Tap Build Number 7 times. Then go to Settings -> System -> Developer options and enable USB debugging).
3.  **Run the App:** In Android Studio, click the "Run" button (green play icon) or navigate to `Run > Run 'app'`. Select your connected device or emulator from the device chooser.

## 4. Creating a Signed APK (Release APK)

To distribute your app on the Google Play Store or other channels, you need to sign it with a digital certificate.

1.  **Generate a Keystore:**
    *   Navigate to `Build > Generate Signed Bundle / APK...`
    *   Select "APK" and click "Next".
    *   Choose "Create new..." to create a new keystore.
    *   Enter the following information:
        *   **Key store path:**  The location where the keystore file will be saved (e.g., `my-release-key.keystore`).
        *   **Password:** A strong password for the keystore.
        *   **Alias:** A name for the key (e.g., `my-key-alias`).
        *   **Key password:** A strong password for the key.
        *   **Validity (years):**  Set the validity period for the key (e.g., 25 years).
        *   **Certificate information:** Enter your name, organization, etc.
    *   Click "OK".
2.  **Configure Build Variants:**
    *   Open the `build.gradle` file for the `app` module (`app/build.gradle`).
    *   Add the following code inside the `android` block:

```gradle
android {
    ...
    signingConfigs {
        release {
            storeFile file("my-release-key.keystore") // Replace with your keystore file
            storePassword "keystore_password" // Replace with your keystore password
            keyAlias "my-key-alias" // Replace with your key alias
            keyPassword "key_password" // Replace with your key password
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true  // Enable code shrinking (optional, but recommended for release builds)
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```
    *   **Important:** Replace `my-release-key.keystore`, `keystore_password`, `my-key-alias`, and `key_password` with your actual keystore file path, passwords, and alias.  **Do not commit these credentials to your version control system.** Consider using environment variables or other secure methods to manage them.
3.  **Build Signed APK:**
    *   Navigate to `Build > Generate Signed Bundle / APK...`
    *   Select "APK" and click "Next".
    *   Choose "release" as the build variant.
    *   Click "Finish".
    *   Android Studio will build a signed APK. The location of the APK is shown in the "Build" tab at the bottom of Android Studio. It typically is in `app/build/outputs/apk/release/app-release.apk`

## 5. Testing the Release APK

1.  **Uninstall Debug Version:** If you have a debug version of the app installed on your device, uninstall it.
2.  **Install Release APK:** Connect your device to your computer and use `adb install app-release.apk` (replace `app-release.apk` with the actual name of your signed APK file) or use Android Studio's APK installation feature to install the signed APK.
3.  **Test Thoroughly:** Test all features of the app to ensure they are working correctly.

## 6. Distribution

You can distribute the signed APK through various channels, such as:

*   **Google Play Store:** Upload the APK to the Google Play Store.
*   **Direct Download:** Make the APK available for download from your website or other platforms.

## 7. Proguard Configuration (Optional)

If you enable code shrinking with Proguard, you may need to configure Proguard rules to prevent it from removing or obfuscating code that is used by reflection or other dynamic mechanisms.  Create a `proguard-rules.pro` file in your `app` module and add any necessary rules.

## 8. Important Considerations

*   **Keystore Security:**  Protect your keystore file and passwords. If you lose your keystore, you will not be able to update your app.
*   **Testing:** Thoroughly test your app on different devices and Android versions before releasing it.
*   **Updates:** Plan for future updates and ensure you have a process for signing and distributing them.
*   **Backup:** Backup your keystore and signing configuration.
