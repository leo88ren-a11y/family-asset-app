package com.familyasset.app

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.CookieManager
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
        // 生产环境地址（带版本参数，强制 WebView 不用缓存）
        private const val H5_BASE_URL = "http://101.34.58.166"
        private const val H5_VERSION = "v2"
        private const val H5_URL = "$H5_BASE_URL?$H5_VERSION"
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
        
        // 每次启动清除 WebView 缓存，确保加载最新前端
        clearWebViewCache()
        
        setupWebView()
        
        // 始终加载最新 URL，不用 savedInstanceState 恢复旧页面
        webView.loadUrl(H5_URL)
    }
    
    private fun clearWebViewCache() {
        webView.clearCache(true)
        webView.clearHistory()
        webView.clearFormData()
        CookieManager.getInstance().removeAllCookies(null)
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
            // 禁用 WebView 缓存，始终从服务器加载最新资源
            cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
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
            override fun onShowFileChooser(
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
    
    // 删除 saveState/restoreState — 不再恢复旧 WebView 状态，避免缓存旧页面
}