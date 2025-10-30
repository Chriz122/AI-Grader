a=float(input("請輸入身高(cm):"))
b=float(input("請輸入體重(kg):"))
#身高公分換公尺
c=a/100
#換算bmi
bmi=b/(c**2)
print("身體質量指數:",round(bmi))
#計算男生理想體重
boy=(a-80)*0.7
#計算女生理想體重
girl=(a-70)*0.6
print("男生理想體重(kg):",round(boy))
print("女生理想體重(kg):",round(girl))

