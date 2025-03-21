'use strict';

// Import Firebase SDK
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js';
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut, onAuthStateChanged } from 'https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js';

// Firebase Configuration
const firebaseConfig = {
    apiKey: "AIzaSyBaixz7wynw0s93HxQPbdMQIOcfIPeOxps",
    authDomain: "formula1-a888d.firebaseapp.com",
    projectId: "formula1-a888d",
    storageBucket: "formula1-a888d.firebasestorage.app",
    messagingSenderId: "135717309658",
    appId: "1:135717309658:web:8ed707426f8bae73ee29e3"
  };

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Prevent infinite redirects using session storage
const hasRedirected = sessionStorage.getItem("authRedirected");

// Handle authentication state changes
onAuthStateChanged(auth, (user) => {
    if (user) {
        console.log("User is logged in:", user.email);

        // Redirect to dashboard only if not already there
        if (window.location.pathname === "/" && !hasRedirected) {
            sessionStorage.setItem("authRedirected", "true"); // Prevent loop
            window.location.href = "/dashboard";
        }
    } else {
        console.log("User is not logged in");

        // Redirect to login page only if on dashboard
        if (window.location.pathname === "/dashboard") {
            window.location.href = "/";
        }
    }
});

// Attach event listeners only once after the DOM is loaded
window.addEventListener("load", function () {
    console.log("Firebase authentication script loaded");

    // Attach event listener for Sign Up button
    const signUpButton = document.getElementById("sign-up");
    if (signUpButton) {
        signUpButton.addEventListener('click', function () {
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;

            createUserWithEmailAndPassword(auth, email, password)
                .then((userCredential) => {
                    const user = userCredential.user;

                    user.getIdToken().then((token) => {
                        document.cookie = "token=" + token + "; path=/; SameSite=Strict";
                        console.log("User signed up successfully.");
                        sessionStorage.setItem("authRedirected", "false"); // Reset redirect flag
                        window.location.href = "/dashboard";  // Redirect after sign-up
                    });
                })
                .catch((error) => {
                    console.error("Error during sign-up:", error.message);
                    alert("Sign-up failed: " + error.message);
                });
        });
    }

    // Attach event listener for Login button
    const loginButton = document.getElementById("login");
    if (loginButton) {
        loginButton.addEventListener('click', function () {
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;

            signInWithEmailAndPassword(auth, email, password)
                .then((userCredential) => {
                    const user = userCredential.user;

                    user.getIdToken().then((token) => {
                        document.cookie = "token=" + token + "; path=/; SameSite=Strict";
                        console.log("User logged in successfully.");
                        sessionStorage.setItem("authRedirected", "false"); // Reset redirect flag
                        window.location.href = "/dashboard";  // Redirect after login
                    });
                })
                .catch((error) => {
                    console.error("Login error:", error.message);
                    alert("Login failed: " + error.message);
                });
        });
    }

    // Attach event listener for Sign Out button
    const signOutButton = document.getElementById("sign-out");
    if (signOutButton) {
        signOutButton.addEventListener('click', function () {
            signOut(auth).then(() => {
                document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
                sessionStorage.setItem("authRedirected", "false"); // Reset redirect flag
                console.log("User signed out.");
                window.location.href = "/";  // Redirect to login page after logout
            }).catch((error) => {
                console.error("Sign-out error:", error.message);
                alert("Sign-out failed: " + error.message);
            });
        });
    }
});
