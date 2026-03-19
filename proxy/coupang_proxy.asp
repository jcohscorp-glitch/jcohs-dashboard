<%@ Language="VBScript" %>
<%
' ============================================================
'  쿠팡 API 프록시 (Classic ASP)
'  Streamlit Cloud -> 이 서버(고정IP) -> 쿠팡 API
' ============================================================
Option Explicit
Response.ContentType = "application/json"
Response.Charset = "utf-8"

Const PROXY_SECRET = "jcohs-coupang-proxy-2026-secret"

' -- 인증 --
Dim authHeader
authHeader = Request.ServerVariables("HTTP_X_PROXY_AUTH")
If authHeader <> PROXY_SECRET Then
    Response.Write "{""proxy_status"":403,""proxy_error"":""Unauthorized""}"
    Response.End
End If

' -- 파라미터 (헤더에서 읽기) --
Dim targetMethod, targetPath, targetAuth
targetMethod = Request.ServerVariables("HTTP_X_CP_METHOD")
targetPath   = Request.ServerVariables("HTTP_X_CP_PATH")
targetAuth   = Request.ServerVariables("HTTP_X_COUPANG_AUTH")

If targetMethod = "" Then targetMethod = "GET"
If targetPath = "" Then
    Response.Write "{""proxy_status"":400,""proxy_error"":""X-Cp-Path header required""}"
    Response.End
End If

' -- POST/PUT body --
Dim targetBody
targetBody = ""
If targetMethod = "POST" Or targetMethod = "PUT" Then
    If Request.TotalBytes > 0 Then
        Dim stream
        Set stream = Server.CreateObject("ADODB.Stream")
        stream.Open
        stream.Type = 1
        stream.Write Request.BinaryRead(Request.TotalBytes)
        stream.Position = 0
        stream.Type = 2
        stream.Charset = "utf-8"
        targetBody = stream.ReadText
        stream.Close
        Set stream = Nothing
    End If
End If

' -- 쿠팡 API 호출 --
Dim targetUrl
targetUrl = "https://api-gateway.coupang.com" & targetPath

Dim http
Set http = Server.CreateObject("MSXML2.ServerXMLHTTP.6.0")
http.SetTimeouts 5000, 10000, 30000, 60000

On Error Resume Next
http.Open targetMethod, targetUrl, False
http.SetRequestHeader "Authorization", targetAuth
http.SetRequestHeader "Content-Type", "application/json;charset=UTF-8"
http.SetRequestHeader "X-Requested-By", "JCOHS-Dashboard"
http.SetRequestHeader "X-EXTENDED-TIMEOUT", "90000"

' -- 추가 헤더 패스스루 (X-Cp-Hdr-* -> *) --
Dim xMarket
xMarket = Request.ServerVariables("HTTP_X_CP_HDR_X_MARKET")
If xMarket <> "" Then
    http.SetRequestHeader "X-MARKET", xMarket
End If

If targetMethod = "POST" Or targetMethod = "PUT" Then
    http.Send targetBody
Else
    http.Send
End If

If Err.Number <> 0 Then
    Response.Write "{""proxy_status"":502,""proxy_error"":""" & Replace(Err.Description, """", "\""") & """}"
    Response.End
End If
On Error GoTo 0

' -- 항상 200으로 응답 --
Dim actualStatus, actualBody
actualStatus = http.Status
actualBody = http.ResponseText

Set http = Nothing

If actualStatus = 200 Then
    Response.Write actualBody
Else
    Response.Write "{""proxy_status"":" & actualStatus & ",""proxy_body"":" & Chr(34) & Replace(Replace(actualBody, "\", "\\"), Chr(34), "\""") & Chr(34) & "}"
End If
%>
