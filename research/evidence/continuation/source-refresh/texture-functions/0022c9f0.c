
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../modules4/graphics/textpage.c:172, 260 */

int FUN_0022c9f0(long param_1,int param_2,int param_3)

{
  int iVar1;
  int iVar2;
  int iVar3;
  
  if (param_1 == 8) {
    if ((param_2 == param_3) || ((0x7f < param_2 && (0x3f < param_3)))) {
      iVar2 = param_2 * 8 * param_3;
    }
    else {
      if ((param_2 == 0x40) && (param_3 == 0x20)) {
        iVar2 = 0x4000;
        goto LAB_0022cd18;
      }
      if (0x80 < param_2) {
        iVar2 = param_3 + 0x3f;
        if (param_3 + 0x3f < 0) {
          iVar2 = param_3 + 0x7e;
        }
        param_3 = (iVar2 >> 6) << 6;
      }
      if ((param_2 == 0x80) && (param_3 < 0x40)) {
        param_3 = 0x40;
      }
      else if ((param_2 == 0x40) && (param_3 < 0x20)) {
        param_3 = 0x20;
      }
      iVar2 = param_2 + 0xf;
      if (param_2 + 0xf < 0) {
        iVar2 = param_2 + 0x1e;
      }
      iVar1 = param_3 + 0xf;
      if (param_3 + 0xf < 0) {
        iVar1 = param_3 + 0x1e;
      }
      iVar2 = (iVar2 >> 4) << 7;
      param_3 = (iVar1 >> 4) << 4;
LAB_0022ccf0:
      iVar2 = iVar2 * param_3;
    }
  }
  else if (param_1 < 9) {
    if (param_1 != 4) {
LAB_0022cd00:
                    /* WARNING: Subroutine does not return */
      FUN_00105888(0x250b68,0x104,0x250bb0,param_1);
    }
    if ((param_2 != param_3) && ((param_2 < 0x80 || (param_3 < 0x80)))) {
      iVar2 = param_3;
      if ((param_2 == 0x80) && (iVar2 = 0x40, 0x3f < param_3)) {
        iVar2 = param_3;
      }
      if (param_2 < 0x81) {
        if ((param_2 == 0x40) && (iVar2 < 0x40)) {
          iVar2 = 0x40;
        }
      }
      else {
        iVar1 = iVar2 + 0x7f;
        if (iVar2 + 0x7f < 0) {
          iVar1 = iVar2 + 0xfe;
        }
        iVar2 = (iVar1 >> 7) << 7;
      }
      iVar1 = param_2 + 0x1f;
      if (param_2 + 0x1f < 0) {
        iVar1 = param_2 + 0x3e;
      }
      iVar3 = iVar2 + 0xf;
      if (iVar2 + 0xf < 0) {
        iVar3 = iVar2 + 0x1e;
      }
      iVar2 = (iVar1 >> 5) << 7;
      param_3 = (iVar3 >> 4) << 4;
      goto LAB_0022ccf0;
    }
    iVar2 = param_2 * 4 * param_3;
  }
  else {
    if (param_1 != 0x10) {
      if (param_1 != 0x20) goto LAB_0022cd00;
      iVar2 = param_2 << 5;
      if (param_2 != param_3) {
        if ((param_2 < 0x40) || (param_3 < 0x20)) {
          if ((param_2 == 0x20) && (param_3 == 0x10)) {
            iVar2 = 0x4000;
            goto LAB_0022ccf4;
          }
          if (0x40 < param_2) {
            iVar2 = param_3 + 0x1f;
            if (param_3 + 0x1f < 0) {
              iVar2 = param_3 + 0x3e;
            }
            param_3 = (iVar2 >> 5) << 5;
          }
          if ((param_2 == 0x40) && (param_3 < 0x20)) {
            param_3 = 0x20;
          }
          else if ((param_2 == 0x20) && (param_3 < 0x10)) {
            param_3 = 0x10;
          }
          iVar2 = param_2 + 7;
          if (param_2 + 7 < 0) {
            iVar2 = param_2 + 0xe;
          }
          iVar1 = param_3 + 7;
          if (param_3 + 7 < 0) {
            iVar1 = param_3 + 0xe;
          }
          iVar2 = (iVar2 >> 3) << 8;
          param_3 = (iVar1 >> 3) << 3;
        }
        else {
          iVar2 = param_2 << 5;
        }
      }
      goto LAB_0022ccf0;
    }
    if ((param_2 != param_3) && ((param_2 < 0x40 || (param_3 < 0x40)))) {
                    /* WARNING: Subroutine does not return */
      FUN_00105888(0x250b68,0xac,0x250b88);
    }
    iVar2 = param_2 * 0x10 * param_3;
  }
LAB_0022ccf4:
  iVar2 = iVar2 + 0x7ff;
LAB_0022cd18:
  return iVar2 >> 0xb;
}

