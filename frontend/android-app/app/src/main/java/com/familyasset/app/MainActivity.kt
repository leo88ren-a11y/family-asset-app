package com.familyasset.app

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature

class MainActivity : AppCompatActivity() {
    
    private lateinit var webView: WebView
    private var filePathCallback: android.webkit.ValueCallback<Array<Uri>>? = null
    
    companion object {
        // 生产环境地址
        private const val H5_URL = "http://101.34.58.166"
    }
    
    // 文件选择器 launcher
    private val fileChooserLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val uris = mutableListOf<Uri>()
            result.data?.let { intent ->
                val clipData = intent.clipData
                if (clipData != null) {
                    for (i in 0 until clipData.itemCount) {
                        clipData.getItemAt(i).uri?.let { uris.add(it) }
                    }
                } else {
                    intent.data?.let { uris.add(it) }
                }
            }
            if (uris.isNotEmpty()) {
                filePathCallback?.onReceiveValue(uris.toTypedArray())
            } else {
                filePathCallback?.onReceiveValue(null)
            }
        } else {
            filePathCallback?.onReceiveValue(null)
        }
        filePathCallback = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        webView = findViewById(R.id.webView)
        setupWebView()
        
        if (savedInstanceState == null) {
            webView.loadUrl(H5_URL)
        }
    }
    
    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            setSupportZoom(false)
            builtInZoomControls = false
            displayZoomControls = false
            useWideViewPort = true
            loadWithOverviewMode = true
            mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
        }
        
        // 支持深色模式
        if (WebViewFeature.isFeatureSupported(WebViewFeature.FORCE_DARK)) {
            WebSettingsCompat.setForceDark(webView.settings, WebSettingsCompat.FORCE_DARK_AUTO)
        }
        
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                return false
            }
        }
        
        webView.webChromeClient = object : WebChromeClient() {
            // 处理 HTML input type="file"
            fun openFileChooser(uploadMsg: android.webkit.ValueCallback<Array<Uri>>, acceptType: String, capture: String) {
                filePathCallback = uploadMsg as android.webkit.ValueCallback<Array<Uri>>?
                val intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.type = "image/*"
                fileChooserLauncher.launch(intent)
            }
            
            // Android 5.0+ 需要这个方法
            fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: android.webkit.ValueCallback<Array<Uri>>?,
                fileChooserParams: android.webkit.WebChromeClient.FileChooserParams?
            ): Boolean {
                this@MainActivity.filePathCallback = filePathCallback
                val intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.type = "image/*"
                fileChooserLauncher.launch(intent)
                return true
            }
        }
    }
    
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
    
    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }
    
    override fun onRestoreInstanceState(savedInstanceState: Bundle) {
        super.onRestoreInstanceState(savedInstanceState)
        webView.restoreState(savedInstanceState)
    }
}