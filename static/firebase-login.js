'use strict';
  // Import the functions you need from the SDKs you need
  import { initializeApp } from "https://www.gstatic.com/firebasejs/11.3.1/firebase-app.js";
  // TODO: Add SDKs for Firebase products that you want to use
  import{getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut} from  "https://www.gstatic.com/firebasejs/11.3.1/firebase-auth.js";

  // Your web app's Firebase configuration
  // Firebase Configuration
const firebaseConfig = {
    apiKey: "AIzaSyBaixz7wynw0s93HxQPbdMQIOcfIPeOxps",
    authDomain: "formula1-a888d.firebaseapp.com",
    projectId: "formula1-a888d",
    storageBucket: "formula1-a888d.firebasestorage.app",
    messagingSenderId: "135717309658",
    appId: "1:135717309658:web:8ed707426f8bae73ee29e3"
  };

  window.addEventListener("load",function(){
    const app = initializeApp(firebaseConfig);
    const auth=getAuth(app);
    updateUI(this.document.cookie);
    console.log("hello world load");
    
    document.getElementById("sign-up").addEventListener('click',function(){
        const email=document.getElementById("email").value
        const password=document.getElementById("password").value 

        createUserWithEmailAndPassword(auth,email,password)
        .then((userCredentials)=>{
            const user=userCredentials.user;

            user.getIdToken().then((token)=>{
                document.cookie="token="+token+";path=/;SameSite=Strict";
                window.location="/";
            });
        })
        .catch((error)=>{
            console.log(error.code+error.message);
        })
    });

    this.document.getElementById("login").addEventListener('click',function(){
        const email=document.getElementById("email").value
        const password=document.getElementById("password").value

        signInWithEmailAndPassword(auth,email,password)
        .then((userCredentials)=>{
            const user=userCredentials.user;
            console.log("looged in");

            user.getIdToken().then((token)=>{
                document.cookie="token="+token+";path=/;SameSite=Strict";
                window.location="/";
            });
        })
        .catch((error)=>{
            console.log(error.code+error.message)
        })
    });

    this.document.getElementById("sign-out").addEventListener('click', function(){
        signOut(auth)
        .then((output)=>{
            document.cookie="token=;path=/;SameSite=Strict";
            window.location="/";
        })
    });
});

function updateUI(cookie){
    var token=parseCookieToken(cookie);

    if (token.length>0){
        document.getElementById("login-box").hidden=true;
        document.getElementById("sign-out").hidden=false;
    }
    else{
        document.getElementById("login-box").hidden=false;
        document.getElementById("sign-out").hidden=true;
    }
}

function parseCookieToken(cookie){
    var strings=cookie.split(";");

    for (let i=0;i<strings.length;i++){
        var temp=strings[i].split('=');
        if(temp[0]=="token")
            return temp[1];
    }
    return "";
}