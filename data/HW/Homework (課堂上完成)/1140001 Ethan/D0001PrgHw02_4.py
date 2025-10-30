#資料輸入
print("\t\t/**這是可算出身體質量指數BMI與理想體重的程式**/\n")
H=float(input("\t\t請輸入身高(cm):"))
W=float(input("\t\t請輸入體重(kg):"))

#身高換算
M=H/100

#計算BMI
BMI=W/(M**2)

#計算理想體重
#男生理想體重(kg)=(身高(cm)-80)*0.7
idealmale=(H-80)*0.7
    
#女生理想體重(kg)=(身高(cm)-70)*0.6
idealwoman=(H-70)*0.6

#輸出BMI
print(f"您的身體質量指數 (BMI) 為: {BMI:.2f}")
    
#輸出理想體重
print(f"男生理想體重應為: {idealmale:.2f} kg")
print(f"女生理想體重應為: {idealwoman:.2f} kg")