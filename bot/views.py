from django.shortcuts import render

# Create your views here.


# For callback
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

# request abnormal handle
from linebot import LineBotApi, WebhookParser, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError

# request message handle
from linebot.models import MessageEvent, TextSendMessage, ImageSendMessage

# databast
from trips.models import Post, PersonalInfo

# upload img
import os
from imgurpython import ImgurClient

# match request str
import re

# time
from datetime import datetime, timedelta


# Line API info
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)


@csrf_exempt
def callback(request):

    if request.method == 'POST':

        # request.META 是一个Python字典，包含了所有本次HTTP请求的Header信息
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')

        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent):

                # 分析訊息事件內容後回傳SendMessage instance
                reply_msg = Reply(event)
                line_bot_api.reply_message(
                    event.reply_token,
                    reply_msg
                )
        return HttpResponse()
    else:
        return HttpResponseBadRequest()


def Reply(event):

    message_type = event.message.type

    userId = event.source.user_id
    profile = line_bot_api.get_profile(userId)
    userName = profile.display_name

    person_list = PersonalInfo.objects.all()

    # 檢查此用戶是否註冊，若無則無法使用機器人功能
    user_profile = person_list.filter(user_id=userId)

    # 未註冊用戶之處理流程
    if len(user_profile) == 0:

        # 紀錄此次未註冊用戶並通知管理者
        report = "User Name={0}\nUser ID={1}".format(userName, userId)
        Post.objects.create(title='unregister', content=report)
        notify_Manager("有未註冊用戶嘗試使用Chatbot")

        return TextSendMessage(text='親愛的用戶您尚未註冊，恕暫時無法開通機器人功能，已通知管理員盡快為您註冊。')

    # 回覆已註冊用戶的文字訊息
    if message_type == 'text':

        text = event.message.text

        captcha_post_title = 'Thsrc_captcha_' + userId[:10]

        # 檢查此次訊息是否為驗證碼
        isCaptcha_text = len(Post.objects.all().filter(
            title=captcha_post_title)) > 0

        if isCaptcha_text:

            captcha_posts = Post.objects.all().filter(title=captcha_post_title)

            pid_rx = int(captcha_posts[0].content)

            captcha_posts.update(content=text)

            send_signal(pid_rx)

            reply_text = '已回覆驗證碼'

        elif '留言：' in text:
            colon = text.find('：')
            key_text = text[colon + 1:]
            Post.objects.all().filter(title='last_message').update(content=key_text)

            reply_text = "已確認留言：\n< " + key_text + \
                " > ,\n 並上傳至官網:https://taipei-drifter.herokuapp.com/brocast/"

        elif '存入：' in text:

            colon = text.find('：')
            key_text = text[colon + 1:]
            Post.objects.all().filter(title='for_test_post').update(content=key_text)

            reply_text = '存入完成!!'

        elif '提取' in text:

            reply_text = str(Post.objects.all().filter(
                title='for_test_post')[0].content)

        elif 'pid' in text:

            reply_text = str(os.getpid())

        elif 'wait' in text:

            reply_text = '收到信號' if wait_signal(20) else '未收到信號'

        elif 'signal' in text:

            reply_text = send_signal(int(text[-1]))

        elif '高鐵' in text:

            from selenium import webdriver
            from selenium.webdriver.support.select import Select
            from PIL import Image

            print('準備開啟Driver')

            # 設定 Chrome driver
            chrome_options = webdriver.ChromeOptions()
            chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--headless')
            chrome_options.add_argument(
                '--disable-dev-shm-usage')  # IMPORTANT !!!
            chrome_driver_path = os.getenv('CHROMEDRIVER_PATH')

            try:
                Browser = webdriver.Chrome(
                    executable_path=chrome_driver_path, chrome_options=chrome_options)
            except ConnectionResetError:
                pass

            line_bot_api.push_message(userId, TextSendMessage(text='驗證碼抓取中..'))

            # 開啟高鐵網頁
            WebUrl = ('https://irs.thsrc.com.tw/IMINT/?student=university')
            Browser.get(WebUrl)

            # 抓取驗證碼圖形
            img_path = os.path.join('/tmp', 'screenshot.png')
            captcha_path = os.path.join('/tmp', 'captcha.png')

            Browser.save_screenshot(img_path)

            if os.path.exists(img_path):
                print('照片儲存成功')

            im = Image.open(img_path)
            nim = im.crop((351, 484, 475, 522))
            nim.save(captcha_path)

            print('圖片上傳中...')
            img_url = upload_img(captcha_path)

            # 回傳驗證碼圖形給使用者
            line_bot_api.push_message(userId, ImageSendMessage(
                original_content_url=img_url, preview_image_url=img_url))

            line_bot_api.push_message(
                userId, TextSendMessage(text='請輸入驗證碼(打快一點你只有15秒)'))

            # 設置資料庫captcha post
            captcha_post_title = 'Thsrc_captcha_' + userId[:10]  # 附上user id前十碼

            captcha_post_content = str(os.getpid())

            Post.objects.create(title=captcha_post_title,
                                content=captcha_post_content)

            captcha_posts = Post.objects.all().filter(title=captcha_post_title)

            # 填入時刻表資訊,抓出驗證碼欄位及送出鈕
            select_day = (datetime.now() + timedelta(hours=8)
                          ).strftime("%Y/%m/%d")

            time_moment = (datetime.now() + timedelta(hours=8)
                           ).hour

            time_moment = 2 * time_moment - 9

            fill_THSRC_form(Browser, 12, 2, select_day, time_moment)

            captcha_field = Browser.find_element_by_name(
                'homeCaptcha:securityCode')

            submit_buttom = Browser.find_element_by_id('SubmitButton')

            # 設置Signal Handler,等待使用者回傳驗證碼
            isReceiveCaptcha = wait_signal(15)

            # 收到Captcha：填入驗證碼 並送出請求
            if isReceiveCaptcha:

                captcha_code = captcha_posts[0].content

                captcha_field.send_keys(captcha_code)

                submit_buttom.click()

                # 驗證碼正確：存下並回傳瀏覽器快照
                if len(Browser.find_elements_by_class_name('feedbackPanelERROR')) == 0:

                    Browser.save_screenshot('/tmp/timetable.png')

                    train_num = len(
                        Browser.find_elements_by_id('QueryArrival'))

                    row_width = 34.5

                    im_table = Image.open('/tmp/timetable.png')

                    im_table = im_table.crop(
                        (110, 230, 775, 230 + train_num * row_width))

                    im_table.save('/tmp/timetable.png')

                    reply_image_url = upload_img('/tmp/timetable.png')

                # 驗證碼錯誤：回傳驗證碼錯誤issue
                else:

                    reply_text = '驗證碼錯誤'

            # 未收到Captcha：回傳逾時issue
            else:
                reply_text = '驗證碼時效逾期QQ'

            # 刪除captcha欄位
            captcha_posts.delete()

            # 關閉瀏覽器
            Browser.quit()

        else:

            reply_image_url = "https://ae01.alicdn.com/kf/HTB12CDaPXXXXXcAXFXXq6xXFXXXs/Wholesale-10pcs-lot-20pcs-lot-Middle-Finger-Funny-Jdm-Car-Sticker-Car-Rear-Windshield-Car-Body.jpg_640x640.jpg"

    # 回覆圖片訊息
    elif message_type == 'image':

        message_content = line_bot_api.get_message_content(event.message.id)

        img_path = os.path.join('/tmp', 'example.jpg')

        with open(img_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)

        line_bot_api.push_message(userId, TextSendMessage(text='圖片上傳中...'))

        # 上傳至Imgur
        img_url = upload_img(img_path)

        # 上傳至個人後台資料庫

        img_url_set = user_profile[0].img_url_set
        img_url_date = user_profile[0].img_url_date
        img_url_num = user_profile[0].img_url_num

        today_format = (datetime.now() + timedelta(hours=8)
                        ).strftime("%Y/%m/%d")

        if img_url_num == 0:  # 首張圖片
            img_url_set = img_url
            img_url_date = today_format
            img_url_num += 1

        else:  # 非首張
            img_url_set = img_url_set + '::' + img_url
            img_url_date = img_url_date + '::' + today_format
            img_url_num += 1

        user_profile.update(img_url_set=img_url_set,
                            img_url_date=img_url_date, img_url_num=img_url_num)

        # 上傳至網頁資料庫
        Post.objects.all().filter(title='last_photo').update(content=userName)
        Post.objects.all().filter(title='last_photo').update(photo=img_url)

        reply_text = "圖片已上傳成功，網址為：\n{0}".format(
            "https://taipei-drifter.herokuapp.com/brocast/")

    try:  # Text Reply
        reply_msg = TextSendMessage(text=reply_text)
    except NameError:  # Image Reply
        reply_msg = ImageSendMessage(
            original_content_url=reply_image_url, preview_image_url=reply_image_url)

    return reply_msg


# 上傳圖片至imgur.com
def upload_img(img_path):

    from .configure import client_id, client_secret, access_token, refresh_token

    client = ImgurClient(client_id, client_secret, access_token, refresh_token)

    image = client.upload_from_path(img_path)

    return image['link']


# 註冊本機器人應用程式
def registerMyBot(userName, userId):

    user_profile = person_list.filter(user_id=userId)

    if len(user_profile) == 0:
        PersonalInfo.objects.create(user_name=userName, user_id=userId)


# 通知管理員
def notify_Manager(notice):

    from .configure import manager_id

    line_bot_api.push_message(
        manager_id, TextSendMessage(text='[系統推播]:\n' + notice))


# 等待信號(或請求過期)
def wait_signal(clock):

    from time import sleep
    import signal

    event = False
    count_sec = 0

    print('PID = {0}'.format(os.getpid()))

    def handler(sig, frame):
        nonlocal event
        event = True

    signal.signal(signal.SIGUSR1, handler)

    while event == False and count_sec < clock:
        count_sec += 1
        sleep(1)
        print('wait...({0})'.format(count_sec))

    return event


# 發送信號
def send_signal(pid_rx):

    import signal

    try:
        os.kill(pid_rx, signal.SIGUSR1)
        return 'Send signal successfully'
    except ProcessLookupError:
        return 'The PID is wrong'


# 操作selenium填表
def fill_THSRC_form(Browser, start, destination, select_day, time_moment):

    from selenium import webdriver
    from selenium.webdriver.support.select import Select

    slector = Select(Browser.find_element_by_css_selector(
        "[name='selectStartStation']"))
    slector.select_by_index(start)

    slector = Select(Browser.find_element_by_css_selector(
        "[name='selectDestinationStation']"))
    slector.select_by_index(destination)

    date_input = Browser.find_element_by_name('toTimeInputField')
    date_input.clear()
    date_input.send_keys(select_day)

    slector = Select(Browser.find_element_by_css_selector(
        "[name='toTimeTable']"))
    slector.select_by_index(time_moment)
