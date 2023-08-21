import csv, os, random, shutil

badge_image_dir = "../badge_images/104 px"

with open('../badge_info.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for raw_row in csv_reader:
        row=[]
        for item in raw_row:
            row.append(item.replace("???",""))
        if line_count == 0:
            #header
            line_count += 1
        else:
            badge_dir = f"./badges/{row[0]}/"
            badge_data_file = os.path.join(badge_dir, f"{row[0]}.txt")
            badge_image = os.path.join(badge_dir, f"{row[0]}.bmp")
            os.makedirs(badge_dir, exist_ok=True)
            with open(badge_data_file, "w") as file1:
                # Writing data to a file
                file1.write(f"{row[2]}\n{row[0]} {row[1]}\n{row[3]}\n\n\n\n\n\n\n{row[4]}\n")
            line_count += 1
            image_pick = random.randint(0,20)
            image_list = [img for img in os.listdir(badge_image_dir)]
            print(image_list)
            print(image_pick)
            image_list.sort()
            sel_img = image_list[image_pick]
            shutil.copyfile(os.path.join(badge_image_dir,sel_img), badge_image)
    print(f'Processed {line_count} lines.')
