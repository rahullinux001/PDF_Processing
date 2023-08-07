import pandas as pd
import pdfplumber
import re


def not_within_bboxes(obj, bboxes):
    def obj_in_bbox(_bbox):
        v_mid = (obj["top"] + obj["bottom"]) / 2
        h_mid = (obj["x0"] + obj["x1"]) / 2
        x0, top, x1, bottom = _bbox
        return (h_mid >= x0) and (h_mid < x1) and (v_mid >= top) and (v_mid < bottom)

    return not any(obj_in_bbox(__bbox) for __bbox in bboxes)


def curves_to_edges(cs):
    edges = []
    for c in cs:
        edges += pdfplumber.utils.rect_to_edges(c)
    return edges


def raw_text_extract(pdf_file):
    page_data = []
    page_bboxes = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            # print("\n\n\n\n\nAll text:")
            # print(page.extract_text())
            page.extract_text()

            # Get the bounding boxes of the tables on the page.
            bboxes = [
                table.bbox
                for table in page.find_tables(
                    table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "explicit_vertical_lines": curves_to_edges(page.curves)
                        + page.edges,
                        "explicit_horizontal_lines": curves_to_edges(page.curves)
                        + page.edges,
                    }
                )
            ]
            page_bboxes.append(bboxes)

            # print("\n\n\n\n\nText outside the tables:")
            page_data.append(
                page.filter(lambda obj: not_within_bboxes(obj, bboxes)).extract_text()
            )
            page_data[-1] = page_data[-1].replace(".  ", ".")
    return page_data, page_bboxes


def header_footer_remove(page_data: list):
    new_page_data = []
    input = page_data.copy()
    for page_idx in range(len(input)):
        page_lines = input[page_idx].split("\n")
        if len(page_lines) > 0 and len(page_lines[-1].strip()) == 0:
            page_lines = page_lines[:-1]
        if len(page_lines) > 0 and page_lines[-1].isnumeric() == True:
            page_lines = page_lines[:-1]
        if len(page_lines) > 1 and page_lines[-2].isnumeric() == True:
            page_lines = page_lines[:-2]
        if len(page_lines) > 0 and "Page" in page_lines[-1]:
            page_lines = page_lines[:-1]
        if len(page_lines) > 1 and "Page" in page_lines[-2]:
            page_lines = page_lines[:-2]
        page_reconstructed = ""
        for line in page_lines:
            page_reconstructed = page_reconstructed + line + "\n"
        input[page_idx] = page_reconstructed

    line_counts = {}
    for page_idx in range(len(input)):
        page_lines = input[page_idx].split("\n")
        for line in page_lines:
            if line in line_counts:
                line_counts[line] = line_counts[line] + 1
            else:
                line_counts[line] = 1
    
    list_remove = []
    for key, value in line_counts.items():
        if len(page_data) <= 7 and value >= len(page_data) - 2 and len(key.strip()) != 0:
            list_remove.append(key)
        elif len(page_data) > 7 and value >= len(page_data) - 4 and len(key.strip()) != 0:
            list_remove.append(key)
    
    for i in range(len(input)):
        t = input[i]
        for value in list_remove:
            t = t.replace(value, "")
        new_page_data.append(t)
    return new_page_data


def check_toc_data(page_data):
    flag_toc = 0
    toc_str = "table of contents"
    toc_start = 0
    while toc_start < len(page_data):
        if toc_str in page_data[toc_start].lower():
            flag_toc = 1
            break
        toc_start = toc_start + 1
    toc_end = toc_start
    while toc_end < len(page_data) and "................" in page_data[toc_end]:
        toc_end += 1
    if flag_toc == 1 and (toc_start == toc_end):
        flag_toc = 0
    return (flag_toc, toc_start, toc_end)


def total_toc_data_fun(page_data, toc_start, toc_end):
    df = pd.DataFrame()
    total_toc_data = ""
    for i in range(toc_start, toc_end):
        x = page_data[i].split("\n")
        x = x[1:]
        x = x[:-1]
        for line in x:
            if "........." in line:
                rev = line[::-1]
                if rev[0] == " ":
                    rev = rev[1:]
                if rev[0].isnumeric() == False:
                    x.remove(line)
        s = ""
        for line in x:
            s += line + "\n"
        total_toc_data += s
    toc = total_toc_data
    toc = toc.replace("\n", " ")
    toc = toc.split(" ")
    toc = " ".join(toc).split()
    l = len(toc)
    for i in range(l):
        if i < l - 3 and toc[i].lower() == "table" and toc[i + 2].lower() == "contents":
            k = i + 2
    content = []
    page_num = []
    flag_num = 1
    number = ""
    word = ""
    for i in range(k + 1, l):
        if "......" in toc[i]:
            word_2 = ""
            number = ""
            rev_num = ""
            num = ""
            j = 0
            while toc[i][j] != ".":
                word_2 += toc[i][j]
                j += 1
            word += word_2
            rev = toc[i][::-1]
            t = 0
            while rev[t] != ".":
                rev_num += rev[t]
                t += 1
            num = rev_num[::-1]
            if num != "":
                flag_num = 1
                number = num
                if word[-1] == " ":
                    word = word[:-1]
                content.append(word)
                page_num.append(number)
                word = ""
            else:
                flag_num = 0
        elif flag_num == 0:
            number += toc[i]
            flag_num = 1
            if word[-1] == " ":
                word = word[:-1]
            content.append(word)
            page_num.append(number)
            word = ""
        elif flag_num == 1:
            word += toc[i] + " "
    df["section_name"] = content
    df["page_no"] = page_num
    return df


def section_segmentation(df, page_data):
    l = len(df)
    s = len(page_data)
    for i in range(len(df)):
        try:
            n_cur = df.iloc[i]["page_no"]
            n_cur = int(n_cur)
            if i != l - 1:
                n_nex = df.iloc[i + 1]["page_no"]
                n_nex = int(n_nex)

            if i < l - 1 and n_cur == n_nex:
                f = page_data[n_cur - 1]
                fidx = f.index(df.iloc[i]["section_name"][:35])
                lidx = f.index(df.iloc[i + 1]["section_name"][:35])
                text = f[fidx + len(df.iloc[i]["section_name"]) : lidx]
                df.at[i, "section_content"] = text
            elif i == l - 1:
                f = page_data[n_cur - 1]
                fidx = f.index(df.iloc[i]["section_name"][:35])
                text = f[fidx + len(df.iloc[i]["section_name"]) : len(f)]
                for j in range(n_cur, s):
                    t = page_data[j]
                    text += t
            elif i < l - 1 and n_cur + 1 == n_nex:
                f = page_data[n_cur - 1]
                fidx = f.index(df.iloc[i]["section_name"][:35])
                text = f[fidx + len(df.iloc[i]["section_name"]) : len(f)]
                k = page_data[n_cur]
                lidx = k.index(df.iloc[i + 1]["section_name"][:35])
                text += k[0:lidx]
            else:
                f = page_data[n_cur - 1]
                fidx = f.index(df.iloc[i]["section_name"][:30])
                text = f[fidx + len(df.iloc[i]["section_name"]) : len(f)]
                q = n_nex
                for j in range(n_cur, q - 1):
                    k = page_data[j]
                    text += k
                k = page_data[q - 1]
                lidx = k.index(df.iloc[i + 1]["section_name"][:35])
                text += k[0:lidx]
            df.at[i, "section_content"] = text
        except:
            df.at[i, "section_content"] = ""


def paragraph_segmentation(df, page_data):
    for j in range(len(df)):
        df.at[j, "paragraph_content"] = ""
        try:
            x = re.split("(\.\)?\s?\n)", df.iloc[j]["section_content"])
            try:
                start_page = df.iloc[j]["page_no"]
            except:
                start_page = df.iloc[j]["section_page_range"][0]
            if j == len(df) - 1:
                end_page = len(page_data)
            else:
                end_page = df.iloc[j + 1]["page_no"]

            para = []
            para_page = []
            for i in range(len(x)):
                if len(x[i]) > 0 and len(x[i].strip()) != 0:
                    if x[i][0] == "." and x[i][-1] == "\n":
                        s = para[-1]
                        para = para[:-1]
                        if x[i][1] == ")":
                            s = s + ")" + "."
                            s = s.replace("\n", " ")
                            para.append(s)
                        else:
                            s = s + "."
                            s = s.replace("\n", " ")
                            para.append(s)
                    else:
                        flag_data_present = 0
                        f = x[i]
                        u = int(start_page) - 1
                        v = int(end_page)
                        if len(para_page) == 0:
                            k = 0
                        else:
                            k = para_page[-1] - 1
                        while k < v:
                            f = f.replace("\n", "")
                            while f[0] == " ":
                                f = f[1:]
                            g = page_data[k]
                            g = g.replace("\n", "")
                            if f in g:
                                flag_data_present = 1
                                para_page.append(k + 1)
                                break
                            k = k + 1
                        if flag_data_present == 0:
                            if len(para_page) == 0:
                                para_page.append(u + 1)
                            else:
                                para_page.append(para_page[-1])
                        x[i] = x[i].replace("\n", " ")
                        para.append(x[i])
        except:
            para = []
            para_page = []
        if len(para) == 0:
            para_tuple = []
        else:
            para_tuple = [(para[c], para_page[c]) for c in range(0, len(para))]
        df.at[j, "paragraph_content"] = para_tuple


def dataframe_generation(page_data, flag_toc, name_of_the_doc, toc_start, toc_end):
    if flag_toc == 1:
        df = total_toc_data_fun(page_data, toc_start, toc_end)
        section_segmentation(df, page_data)
        paragraph_segmentation(df, page_data)
        l = len(page_data)
        for i in range(len(df)):
            list_page = []
            if i == len(df) - 1:
                list_page.append(int(df["page_no"].iloc[i]))
                list_page.append(len(page_data))
                df.at[i, "section_page_range"] = ""
                df.at[i, "section_page_range"] = list_page
            else:
                list_page.append(int(df["page_no"].iloc[i]))
                list_page.append(int(df["page_no"].iloc[i + 1]))
                df.at[i, "section_page_range"] = ""
                df.at[i, "section_page_range"] = list_page
        df = df.drop("page_no", axis=1)

    else:
        df = pd.DataFrame()
        df.at[0, "section_name"] = name_of_the_doc
        list_page = []
        list_page.append(1)
        list_page.append(int(len(page_data)))
        df.at[0, "section_page_range"] = ""
        df.at[0, "section_page_range"] = list_page
        total_data = ""
        for i in range(len(page_data)):
            total_data += page_data[i]
        df["section_content"] = total_data
        paragraph_segmentation(df, page_data)
    return df
