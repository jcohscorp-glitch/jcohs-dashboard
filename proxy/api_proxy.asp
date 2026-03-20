<%@ Language="VBScript" %>
<%
' ============================================================
'  범용 API 프록시 (Classic ASP)
'  Streamlit Cloud -> 이 서버(고정IP) -> 외부 API
'  쿠팡, 네이버 커머스 등 다양한 API에 사용 가능
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
Dim targetMethod, targetUrl, targetContentType
targetMethod = Request.ServerVariables("HTTP_X_TARGET_METHOD")
targetUrl    = Request.ServerVariables("HTTP_X_TARGET_URL")
targetContentType = Request.ServerVariables("HTTP_X_TARGET_CONTENT_TYPE")

If targetMethod = "" Then targetMethod = "GET"
If targetUrl = "" Then
    Response.Write "{""proxy_status"":400,""proxy_error"":""X-Target-Url header required""}"
    Response.End
End If
If targetContentType = "" Then targetContentType = "application/json;charset=UTF-8"

' -- 추가 헤더 (JSON) --
Dim extraHeadersJson
extraHeadersJson = Request.ServerVariables("HTTP_X_TARGET_HEADERS")

' -- POST/PUT body --
Dim targetBody
targetBody = ""
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

' -- API 호출 --
Dim http
Set http = Server.CreateObject("MSXML2.ServerXMLHTTP.6.0")
http.SetTimeouts 5000, 10000, 30000, 60000

On Error Resume Next
http.Open targetMethod, targetUrl, False
http.SetRequestHeader "Content-Type", targetContentType

' -- 추가 헤더 파싱 및 설정 --
If extraHeadersJson <> "" Then
    ' 간단한 JSON 파싱: "key1:value1|key2:value2" 형식
    Dim pairs, pair, parts, i
    pairs = Split(extraHeadersJson, "|")
    For i = 0 To UBound(pairs)
        parts = Split(pairs(i), ":", 2)
        If UBound(parts) >= 1 Then
            http.SetRequestHeader Trim(parts(0)), Trim(parts(1))
        End If
    Next
End If

If targetBody <> "" Then
    http.Send targetBody
Else
    http.Send
End If

If Err.Number <> 0 Then
    Response.Write "{""proxy_status"":502,""proxy_error"":""" & Replace(Err.Description, """", "\""") & """}"
    Response.End
End If
On Error GoTo 0

' -- 항상 200으로 응답 (IIS 에러 페이지 방지) --
Dim actualStatus, actualBody
actualStatus = http.Status
actualBody = http.ResponseText

Set http = Nothing

If actualStatus >= 200 And actualStatus < 300 Then
    Response.Write actualBody
Else
    Response.Write "{""proxy_status"":" & actualStatus & ",""proxy_body"":" & Chr(34) & Replace(Replace(actualBody, "\", "\\"), Chr(34), "\""") & Chr(34) & "}"
End If
%>
