from django.db import models
from django.utils import timezone

class Voucher(models.Model):
    id = models.AutoField(primary_key=True)
    VocId = models.CharField(max_length=255)
    customer = models.CharField(max_length=255)
    companyname = models.CharField(max_length=255)
    concern = models.CharField(max_length=255)
    Mobile = models.CharField(max_length=255)
    amount = models.IntegerField()
    issue_date = models.DateField()
    valid_date = models.DateField()
    status = models.CharField(max_length=1, default='W')
    Branch = models.CharField(max_length=255, db_collation='utf8mb4_unicode_ci')
    bill_no = models.CharField(max_length=255, blank=True, default='')
    bill_date = models.CharField(max_length=255, blank=True, default='')
    Redeemed_Date = models.CharField(max_length=255, blank=True, default='')
    delete_Date = models.CharField(max_length=255, blank=True, default='')
    Verified_Date = models.CharField(max_length=255, blank=True, default='')
    payment_date = models.CharField(max_length=255, blank=True, default='')
    Acc_mng_Verify_date = models.CharField(max_length=255, blank=True, default='')
    Ed_Approved_date = models.CharField(max_length=255, blank=True, default='')
    UTR_No = models.CharField(max_length=255, blank=True, default='')
    UTR_date = models.CharField(max_length=255, blank=True, default='')
    voucherType = models.CharField(max_length=255)
    division = models.CharField(max_length=255)
    creation_utrNo = models.CharField(max_length=255, blank=True, default='')
    print_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'Vouchers'

class ConcernBranchMaster(models.Model):
    id = models.AutoField(primary_key=True)
    Branchid = models.CharField(max_length=255)
    Branchname = models.CharField(max_length=255, db_collation='utf8mb4_unicode_ci')
    concern = models.CharField(max_length=255)
    Branchaddress = models.CharField(max_length=255)
    Branchcity = models.CharField(max_length=255)
    Branchmnemonic = models.CharField(max_length=255)
    Bankaccname = models.CharField(max_length=255)
    Bankaccountnumber = models.CharField(max_length=255)
    Bankbranch = models.CharField(max_length=255)
    Bankname = models.CharField(max_length=255)
    Bankifsc = models.CharField(max_length=255)
    createdAt = models.DateTimeField(default=timezone.now)
    updatedAt = models.DateTimeField(default=timezone.now)
    IAmobile = models.CharField(max_length=255)
    AccmanagerPhone = models.CharField(max_length=255)
    Directorphonenumber = models.CharField(max_length=255)
    Chit_verify_mb = models.CharField(max_length=255)
    IT_head = models.CharField(max_length=255)
    branch_manager = models.CharField(max_length=255)
    Acc_Executive = models.CharField(max_length=255)
    Branch_EDP = models.CharField(max_length=255)
    Branch_IA = models.CharField(max_length=255)

    class Meta:
        db_table = 'CONCERN_BRANCH_MASTER'

class DivisionMaster(models.Model):
    id = models.AutoField(primary_key=True)
    Cocern = models.CharField(max_length=255)
    Branch_Location = models.CharField(max_length=255, db_collation='utf8mb4_unicode_ci')
    Division = models.CharField(max_length=255)
    Status = models.CharField(max_length=255)

    class Meta:
        db_table = 'Division_Master'

class CustomerMaster(models.Model):
    customerTitle = models.CharField(max_length=5, default='')
    customerName = models.CharField(max_length=255, default='')
    email = models.CharField(max_length=255, default='')
    Professional = models.CharField(max_length=50, default='')
    dateOfBirth = models.CharField(max_length=15, default='')
    mobileNo = models.CharField(max_length=15, default='')
    doorNo = models.CharField(max_length=20, default='')
    street = models.CharField(max_length=255, default='')
    area = models.CharField(max_length=255, default='')
    taluk = models.CharField(max_length=50, default='')
    city = models.CharField(max_length=50, default='')
    pinCode = models.CharField(max_length=10, default='')
    state = models.CharField(max_length=50, default='')
    CustomerType = models.CharField(max_length=100, default='')
    purchase_with_sktm = models.CharField(max_length=3, default='No')
    chit_with_sktm = models.CharField(max_length=3, default='No')
    purchase_with_tcs = models.CharField(max_length=3, default='No')
    scm_garments = models.CharField(max_length=3, default='No')
    status = models.CharField(max_length=1, default='P')
    OTP = models.CharField(max_length=8, null=True)
    IsDeleted = models.CharField(max_length=1, default='N')
    CreatedDate = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'CUSTOMERMASTER'

class UTRVoucher(models.Model):
    id = models.AutoField(primary_key=True)
    companyName = models.CharField(max_length=255)
    utrNo = models.CharField(max_length=255, unique=True)
    utrDate = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=1, default='P')
    IsDeleted = models.CharField(max_length=1, default='N')
    CreatedDate = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'UTRVOUCHER'

class ChitsUser(models.Model):
    Sno = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=255)
    MobileNo = models.CharField(max_length=10, unique=True)
    Email = models.CharField(max_length=255)
    City = models.CharField(max_length=255)
    Pincode = models.CharField(max_length=255)
    userType = models.CharField(max_length=255, default='')
    Status = models.CharField(max_length=1, default='A')
    OTP = models.CharField(max_length=255, default='')
    loginTime = models.JSONField(null=True)
    logoutTime = models.JSONField(null=True, default='')
    ipaddress = models.JSONField(null=True, default='')
    location = models.JSONField(null=True, default='')
    isActive = models.BooleanField(default=False)
    Createddate = models.DateTimeField(default=timezone.now)
    Concern = models.CharField(max_length=255)
    Branch = models.CharField(max_length=255)

    class Meta:
        db_table = 'Chits_user'

class UserRoleMaster(models.Model):
    RoleID = models.AutoField(primary_key=True)
    RoleName = models.CharField(max_length=255)
    Chit_Closing = models.CharField(max_length=255)
    Voucher = models.CharField(max_length=255)
    Supplier_Portal = models.CharField(max_length=255)
    Employee_Portal = models.CharField(max_length=255)
    createdAt = models.DateTimeField(default=timezone.now)
    updatedAt = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'USERROLEMASTER'